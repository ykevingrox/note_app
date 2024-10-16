import PyPDF2
import os

def extract_pdf_info(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # 提取标题（使用文件名作为默认标题）
            title = os.path.splitext(os.path.basename(file_path))[0]
            
            # 提取内容
            content = ""
            for page in reader.pages:
                content += page.extract_text() + "\n"
            
            # 提取元数据
            metadata = reader.metadata
            author = metadata.author if metadata.author else "Unknown"
            creation_date = metadata.creation_date if metadata.creation_date else "Unknown"
            
            return {
                'title': title,
                'content': content,
                'author': author,
                'creation_date': str(creation_date),
                'file_path': file_path
            }
    except Exception as e:
        print(f"处理 PDF 文件时出错: {e}")
        return None

