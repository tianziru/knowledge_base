import threading
from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from app.core.logger import logger
from app.conf.embedding_config import embedding_config

# 模型单例对象，避免重复初始化
_bge_m3_ef = None
# 查询图会并行跑向量检索 / HyDE，必须串行初始化/编码，否则易出现 meta tensor 损坏。
# 使用 RLock：generate_embeddings 持锁调用 get_bge_m3_ef 时不能再死锁。
_bge_m3_lock = threading.RLock()


def _reset_bge_m3_ef():
    """丢弃可能已损坏的单例，强制下次重新加载。"""
    global _bge_m3_ef
    _bge_m3_ef = None


def get_bge_m3_ef():
    """
    获取BGE-M3模型单例对象，自动加载环境变量配置
    :return: 初始化完成的BGEM3EmbeddingFunction实例
    """
    global _bge_m3_ef
    # 快路径：已初始化则直接返回
    if _bge_m3_ef is not None:
        logger.debug("BGE-M3模型单例已存在，直接返回实例")
        return _bge_m3_ef

    with _bge_m3_lock:
        # double-check：其他线程可能已在锁内完成初始化
        if _bge_m3_ef is not None:
            logger.debug("BGE-M3模型单例已存在，直接返回实例")
            return _bge_m3_ef

        # 从环境变量加载配置，无配置则使用默认值
        # 本地有可以使用本地地址！ 没有使用 "BAAI/bge-m3" 会自动下载！ 如果云端部署也可以使用url地址！
        model_name = embedding_config.bge_m3_path or "BAAI/bge-m3"
        device = embedding_config.bge_device or "cpu"
        use_fp16 = embedding_config.bge_fp16 or False

        # 打印模型初始化配置，便于问题排查
        logger.info(
            "开始初始化BGE-M3模型",
            extra={
                "model_name": model_name,
                "device": device,
                "use_fp16": use_fp16,
                "normalize_embeddings": True
            }
        )

        try:
            # 初始化BGE-M3模型，开启原生L2归一化（适配Milvus IP内积检索）
            _bge_m3_ef = BGEM3EmbeddingFunction(
                model_name=model_name,
                device=device,
                use_fp16=use_fp16,
                normalize_embeddings=True  # 模型原生对稠密+稀疏向量做L2归一化
            )
            logger.success("BGE-M3模型初始化成功，已开启原生L2归一化")
            return _bge_m3_ef
        except Exception as e:
            _reset_bge_m3_ef()
            logger.error(f"BGE-M3模型初始化失败：{str(e)}", exc_info=True)
            raise  # 向上抛出异常，由调用方处理


def _encode_documents(texts):
    model = get_bge_m3_ef()
    embeddings = model.encode_documents(texts)
    logger.debug(f"模型编码完成，开始解析稀疏向量格式，共{len(texts)}条")

    processed_sparse = []
    for i in range(len(texts)):
        sparse_indices = embeddings["sparse"].indices[
            embeddings["sparse"].indptr[i]:embeddings["sparse"].indptr[i + 1]
        ].tolist()
        sparse_data = embeddings["sparse"].data[
            embeddings["sparse"].indptr[i]:embeddings["sparse"].indptr[i + 1]
        ].tolist()
        sparse_dict = {k: v for k, v in zip(sparse_indices, sparse_data)}
        processed_sparse.append(sparse_dict)

    return {
        "dense": [emb.tolist() for emb in embeddings["dense"]],
        "sparse": processed_sparse
    }


def generate_embeddings(texts):
    """
    为文本列表生成稠密+稀疏混合向量嵌入（模型原生L2归一化）
    :param texts: 要生成嵌入的文本列表，单文本也需封装为列表
    :return: 字典格式的向量结果，key为dense/sparse，对应嵌套列表/字典列表 
    :raise: 向量生成过程中的异常，由调用方捕获处理 
    """
    # 入参合法性校验
    if not isinstance(texts, list) or len(texts) == 0:
        logger.warning("生成向量入参不合法，texts必须为非空列表") 
        raise ValueError("参数texts必须是包含文本的非空列表")          

    logger.info(f"开始为{len(texts)}条文本生成混合向量嵌入")
    try:
        # 编码也加锁，避免初始化刚完成时并发 encode 踩到半初始化权重
        with _bge_m3_lock:
            result = _encode_documents(texts)
        logger.success(f"{len(texts)}条文本向量生成完成，格式已适配工业级使用")
        return result

    except Exception as e:
        err = str(e)
        # 并行初始化损坏后的典型症状：丢掉坏单例，锁内重建并重试一次
        if "meta tensor" in err.lower():
            logger.warning("检测到 meta tensor 异常，重置 BGE-M3 单例并重试一次")
            with _bge_m3_lock:
                _reset_bge_m3_ef()
                try:
                    result = _encode_documents(texts)
                    logger.success(f"{len(texts)}条文本向量生成完成（meta tensor 重试成功）")
                    return result
                except Exception as retry_e:
                    logger.error(f"文本向量生成重试失败：{str(retry_e)}", exc_info=True)
                    raise
        logger.error(f"文本向量生成失败：{err}", exc_info=True)
        raise  # 不吞异常，向上传递让调用方做重试/降级处理


"""
核心设计亮点&适配说明：
1. 模型原生归一化：开启normalize_embeddings = True，自动对稠密+稀疏向量做L2归一化，完美适配Milvus IP内积检索（单位化后IP等价于余弦，计算更快）；
2. 彻底解决NumPy类型做key问题：sparse_indices加.tolist()，将np.int64转为Python原生int，满足字典key的可哈希要求，无报错风险；
3. 稀疏值适配序列化：sparse_data加.tolist()，将np.float32转为Python原生float，支持JSON写入/接口返回/Milvus入库等所有场景；
4. 单例模式优化：模型仅初始化一次，避免重复加载耗时耗资源，提升批量处理效率；
5. 格式匹配业务调用：返回dense嵌套列表、sparse字典列表，与vector_result["dense"][0]/sparse_vector["sparse"][0]取值逻辑完美契合；
6. 分级日志覆盖：从模型初始化、向量生成到异常报错，全流程日志记录，便于生产环境问题排查；
7. 入参合法性校验：防止空列表/非列表入参导致的内部报错，提升工具类健壮性。
"""