"""
初始化脚本 - 从 GitHub 下载后运行

运行此脚本自动完成环境配置
"""
import os
import subprocess
import sys


def init_after_clone():
    """初始化克隆后的环境"""
    
    print("=" * 60)
    print("项目初始化向导")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 步骤 1: 检查 Python 版本
    print("\n[步骤 1] 检查 Python 版本...")
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        print(f"  ✗ Python 版本过低：{python_version.major}.{python_version.minor}")
        print("  需要 Python 3.8 或更高版本")
        return False
    else:
        print(f"  ✓ Python 版本：{python_version.major}.{python_version.minor}")
    
    # 步骤 2: 创建 .env 文件
    print("\n[步骤 2] 创建 .env 文件...")
    env_example_path = os.path.join(base_dir, ".env.example")
    env_path = os.path.join(base_dir, ".env")
    
    if os.path.exists(env_path):
        print(f"  ✓ .env 文件已存在")
    elif os.path.exists(env_example_path):
        # 复制 .env.example 为 .env
        import shutil
        shutil.copy(env_example_path, env_path)
        print(f"  ✓ 已创建 .env 文件（从 .env.example 复制）")
        print(f"  ⚠️ 请编辑 .env 文件，填入你的 API Key")
    else:
        print(f"  ⚠️ 未找到 .env.example，需要手动创建 .env")
    
    # 步骤 3: 创建虚拟环境
    print("\n[步骤 3] 创建虚拟环境...")
    venv_path = os.path.join(base_dir, "venv")
    
    if os.path.exists(venv_path):
        print(f"  ✓ 虚拟环境已存在")
        use_venv = input("  是否重新创建虚拟环境？(y/N): ")
        if use_venv.lower() == 'y':
            import shutil
            shutil.rmtree(venv_path)
            print(f"  ✓ 已删除旧虚拟环境")
        else:
            print(f"  ✓ 使用现有虚拟环境")
    else:
        print(f"  创建虚拟环境...")
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
            print(f"  ✓ 虚拟环境创建成功")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ 创建虚拟环境失败：{e}")
            return False
    
    # 步骤 4: 安装依赖
    print("\n[步骤 4] 安装依赖...")
    requirements_path = os.path.join(base_dir, "requirements.txt")
    
    if not os.path.exists(requirements_path):
        print(f"  ✗ 未找到 requirements.txt")
        return False
    
    # 确定 pip 路径
    if sys.platform == "win32":
        pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        pip_path = os.path.join(venv_path, "bin", "pip")
    
    try:
        print(f"  正在安装依赖...（这可能需要几分钟）")
        subprocess.run(
            [pip_path, "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [pip_path, "install", "-r", requirements_path],
            check=True,
        )
        print(f"  ✓ 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ 安装依赖失败：{e}")
        return False
    
    # 步骤 5: 创建工作目录
    print("\n[步骤 5] 创建工作目录...")
    workspace_path = os.path.join(base_dir, "workspace")
    memory_path = os.path.join(workspace_path, "memory")
    faults_path = os.path.join(workspace_path, ".faults")
    
    os.makedirs(workspace_path, exist_ok=True)
    os.makedirs(memory_path, exist_ok=True)
    os.makedirs(faults_path, exist_ok=True)
    print(f"  ✓ 工作目录已创建：{workspace_path}")
    
    # 步骤 6: 运行测试
    print("\n[步骤 6] 运行测试...")
    test_path = os.path.join(base_dir, "test_migration.py")
    
    if os.path.exists(test_path):
        run_test = input("  是否运行迁移测试？(y/N): ")
        if run_test.lower() == 'y':
            # 激活虚拟环境并运行测试
            if sys.platform == "win32":
                python_path = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                python_path = os.path.join(venv_path, "bin", "python")
            
            try:
                subprocess.run([python_path, test_path], check=True)
                print(f"  ✓ 测试通过")
            except subprocess.CalledProcessError:
                print(f"  ⚠️ 测试失败，但不影响使用")
        else:
            print(f"  ✓ 跳过测试")
    else:
        print(f"  - 未找到测试文件")
    
    # 完成
    print("\n" + "=" * 60)
    print("初始化完成！")
    print("=" * 60)
    
    print("\n📋 下一步:")
    print("  1. 编辑 .env 文件，填入你的 LLM_API_KEY")
    print("  2. 运行示例：python examples\\migration_demo.py")
    print("  3. 运行测试：python test_migration.py")
    print("  4. 查看文档：README.md")
    
    print("\n💡 提示:")
    if sys.platform == "win32":
        print(f"  激活虚拟环境：venv\\Scripts\\activate")
    else:
        print(f"  激活虚拟环境：source venv/bin/activate")
    
    return True


if __name__ == "__main__":
    print("此脚本将帮助你初始化从 GitHub 下载的项目")
    print()
    
    response = input("确定要继续吗？(y/N): ")
    
    if response.lower() == 'y':
        success = init_after_clone()
        if success:
            print("\n✅ 初始化成功！")
            sys.exit(0)
        else:
            print("\n❌ 初始化失败，请检查错误信息")
            sys.exit(1)
    else:
        print("已取消")
        sys.exit(0)
