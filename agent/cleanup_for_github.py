"""
清理脚本 - 删除不需要上传到 GitHub 的文件和目录

运行此脚本后，只保留源文件，可以直接复制整个目录到 GitHub 仓库
"""
import os
import shutil


def cleanup_for_github():
    """清理不需要上传的文件和目录"""
    
    # 需要删除的目录列表
    dirs_to_remove = [
        "venv",
        ".venv", 
        "env",
        "__pycache__",
        ".pytest_cache",
        ".tox",
        ".nox",
        "build",
        "dist",
        "workspace",
        "reports",
        "logs",
        "tmp",
        "temp",
    ]
    
    # 需要删除的文件扩展名
    file_extensions_to_remove = [
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".egg",
        ".egg-info",
        ".log",
        ".coverage",
        ".cover",
    ]
    
    # 需要删除的特定文件
    files_to_remove = [
        ".env",
        ".env.local",
        "pip-log.txt",
        "pip-delete-this-directory.txt",
        "pyvenv.cfg",
        ".DS_Store",
        "Thumbs.db",
    ]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("清理不需要上传到 GitHub 的文件")
    print("=" * 60)
    
    # 删除目录
    print("\n[1] 清理目录...")
    for dirname in dirs_to_remove:
        dir_path = os.path.join(base_dir, dirname)
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"  ✓ 删除目录：{dirname}")
            except Exception as e:
                print(f"  ✗ 无法删除 {dirname}: {e}")
        else:
            print(f"  - 不存在：{dirname}")
    
    # 删除特定文件
    print("\n[2] 清理特定文件...")
    for filename in files_to_remove:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  ✓ 删除文件：{filename}")
            except Exception as e:
                print(f"  ✗ 无法删除 {filename}: {e}")
        else:
            print(f"  - 不存在：{filename}")
    
    # 删除指定扩展名的文件
    print("\n[3] 清理缓存文件...")
    deleted_count = 0
    for root, dirs, files in os.walk(base_dir):
        # 跳过 .git 目录
        if '.git' in dirs:
            dirs.remove('.git')
        
        # 删除 __pycache__ 目录
        if '__pycache__' in dirs:
            try:
                shutil.rmtree(os.path.join(root, '__pycache__'))
                deleted_count += 1
            except:
                pass
        
        # 删除指定扩展名的文件
        for filename in files:
            for ext in file_extensions_to_remove:
                if filename.endswith(ext):
                    file_path = os.path.join(root, filename)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except:
                        pass
    
    print(f"  删除了 {deleted_count} 个缓存文件")
    
    print("\n" + "=" * 60)
    print("清理完成！")
    print("=" * 60)
    
    # 显示保留的文件结构
    print("\n📁 保留的文件结构（可以复制到 GitHub）:")
    print_structure(base_dir)
    
    print("\n💡 提示:")
    print("  1. 现在可以直接复制整个目录到 GitHub 仓库")
    print("  2. .env.example 需要复制为 .env 并配置 API Key")
    print("  3. 运行 'pip install -r requirements.txt' 安装依赖")


def print_structure(path, indent=0, max_depth=3):
    """打印目录结构"""
    if indent > max_depth:
        return
    
    try:
        items = sorted(os.listdir(path))
        
        # 过滤掉不需要的文件
        filtered_items = []
        for item in items:
            if item.startswith('.'):
                if item in ['.git', '.gitignore', '.env.example']:
                    filtered_items.append(item)
            elif item == 'venv' or item == '__pycache__':
                continue
            else:
                filtered_items.append(item)
        
        for i, item in enumerate(filtered_items):
            item_path = os.path.join(path, item)
            is_last = i == len(filtered_items) - 1
            prefix = "└── " if is_last else "├── "
            
            print("    " * indent + prefix + item)
            
            if os.path.isdir(item_path) and indent < max_depth:
                print_structure(item_path, indent + 1, max_depth)
    except PermissionError:
        pass


if __name__ == "__main__":
    response = input("此脚本将删除 venv、__pycache__ 等不需要上传的文件。\n确定要继续吗？(y/N): ")
    
    if response.lower() == 'y':
        cleanup_for_github()
    else:
        print("已取消")
