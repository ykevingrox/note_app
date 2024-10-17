import oss2
import os
from dotenv import load_dotenv
from src.core.logging_config import logger
import sqlite3
import hashlib

load_dotenv()  # 加载 .env 文件中的环境变量

class CloudStorage:
    def __init__(self):
        logger.info("初始化 CloudStorage")
        required_vars = ['OSS_ACCESS_KEY_ID', 'OSS_ACCESS_KEY_SECRET', 'OSS_BUCKET_NAME', 'OSS_ENDPOINT', 'LOCAL_DB_PATH']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            logger.error(f"缺少以下环境变量: {', '.join(missing_vars)}")
            raise ValueError(f"缺少以下环境变量: {', '.join(missing_vars)}")
        
        self.access_key_id = os.environ['OSS_ACCESS_KEY_ID']
        self.access_key_secret = os.environ['OSS_ACCESS_KEY_SECRET']
        self.bucket_name = os.environ['OSS_BUCKET_NAME']
        self.endpoint = os.environ['OSS_ENDPOINT']
        self.local_db_path = os.environ['LOCAL_DB_PATH']
        self.cloud_db_name = 'notes.db'

        try:
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            logger.info("成功初始化 OSS Bucket")
        except oss2.exceptions.OssError as e:
            logger.error(f"初始化 OSS Bucket 失败: {str(e)}")
            raise

    def upload_database(self):
        logger.info("开始上数据库")
        try:
            self.bucket.put_object_from_file(self.cloud_db_name, self.local_db_path)
            logger.info(f"数据库上传成功: {self.cloud_db_name}")
        except oss2.exceptions.OssError as e:
            logger.error(f"数据库上传失败. 错误: {str(e)}", exc_info=True)
            raise

    def download_database(self):
        logger.info("开始下载数据库")
        try:
            self.bucket.get_object_to_file(self.cloud_db_name, self.local_db_path)
            logger.info(f"数据库下载成功: {self.local_db_path}")
        except oss2.exceptions.OssError as e:
            logger.error(f"数据库下载失败. 错误: {str(e)}", exc_info=True)
            raise

    def init_database(self):
        if not os.path.exists(self.local_db_path):
            logger.info(f"本地数据库不存在，尝试从云端下载: {self.local_db_path}")
            self.download_database()
        else:
            try:
                cloud_meta = self.bucket.get_object_meta(self.cloud_db_name)
                local_mtime = os.path.getmtime(self.local_db_path)
                cloud_mtime = cloud_meta.last_modified

                if cloud_mtime > local_mtime:
                    logger.info("云端数据库较新，正在下载...")
                    self.download_database()
                else:
                    logger.info("本地数据库是最新的")
            except oss2.exceptions.NoSuchKey:
                logger.info("云端数据库不存在，将上传本地数据库")
                self.upload_database()

    def update_cloud_database(self):
        self.upload_database()

    def sync_to_cloud(self):
        logger.info("开始同步到云端")
        try:
            self.upload_database()
            logger.info("同步到云端完成")
        except Exception as e:
            logger.error(f"同步到云端失败: {str(e)}", exc_info=True)
            raise

    def close(self):
        logger.info("开始关闭 CloudStorage")
        try:
            self.sync_to_cloud()
            logger.info("CloudStorage 成功关闭")
        except Exception as e:
            logger.error(f"关闭 CloudStorage 时发生错误: {str(e)}", exc_info=True)
            raise

    def get_cloud_file_hash(self, file_name):
        try:
            cloud_file = self.bucket.get_object(file_name)
            hasher = hashlib.md5()
            for chunk in cloud_file:
                hasher.update(chunk)
            return hasher.hexdigest()
        except oss2.exceptions.NoSuchKey:
            logger.warning(f"云端文件 {file_name} 不存在")
            return None
        except Exception as e:
            logger.error(f"获取云端文件哈希值时出错: {str(e)}")
            return None

    def download_database_temp(self):
        temp_path = self.local_db_path + '.temp'
        try:
            self.bucket.get_object_to_file(self.cloud_db_name, temp_path)
            logger.info(f"临时数据库下载成功: {temp_path}")
            return temp_path
        except Exception as e:
            logger.error(f"下载临时数据库时出错: {str(e)}")
            return None

# 可以添加一个测试函数
def test_cloud_storage():
    logger.info("开始测试 CloudStorage")
    try:
        cs = CloudStorage()
        # 您现有的测试代码...
        
        # 测试同步
        cs.sync_to_cloud()
        
        # 测试关闭
        cs.close()
        
        logger.info("CloudStorage 测试成功")
    except Exception as e:
        logger.error(f"CloudStorage 测试失败. 错误: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    test_cloud_storage()
