import shutil
import zipfile
import git
from pathlib import Path
import subprocess
import sys
import os
import requests
import platform
SDK_PATH = Path("./cheese-sdk-win-x64")

def clone_git_repo(repo_url: str, save_path: str) -> bool:

    if os.path.exists(save_path):
        print(save_path+" 已经存在，跳过克隆。")
        return True
    """
    克隆 Git 仓库到指定路径

    Args:
        repo_url: Git仓库链接
        save_path: 本地保存路径

    Returns:
        bool: 是否克隆成功
    """
    try:
        # 设置环境变量代理
        os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
        os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'

        print(f"🔧 代理设置: 127.0.0.1:7897")
        print(f"📥 正在克隆 {repo_url}")
        print(f"📁 目标目录: {save_path}")

        # 克隆仓库
        repo = git.Repo.clone_from(repo_url, save_path)
        print(f"✅ 克隆成功: {save_path}")
        return True

    except Exception as e:
        print(f"❌ 克隆失败: {e}")
        return False


def setup_sdk(sdk_path: str, android_project_path: str = "."):
    """
    设置 SDK 路径并在指定 Android 项目中生成 local.properties

    Args:
        sdk_path: SDK 路径
        android_project_path: Android 项目路径（默认为当前目录）
    """
    # 转换为绝对路径
    sdk_abs = Path(sdk_path).expanduser().resolve()
    project_abs = Path(android_project_path).resolve()

    # 检查 SDK 路径是否存在
    if not sdk_abs.exists():
        print(f"❌ SDK 路径不存在: {sdk_abs}")
        return False

    if not sdk_abs.is_dir():
        print(f"❌ SDK 路径不是目录: {sdk_abs}")
        return False

    # 检查项目路径是否存在
    if not project_abs.exists():
        print(f"❌ 项目路径不存在: {project_abs}")
        return False

    # 检查是否是 Android 项目
    gradle_files = list(project_abs.glob("settings.gradle.kts"))
    if not gradle_files:
        print(f"⚠️  在 {project_abs} 中未找到 settings.gradle.kts 文件")
        return False

    # 处理路径格式
    sdk_str = str(sdk_abs)
    if platform.system() == "Windows":
        sdk_str = sdk_str.replace("\\", "\\\\")

    # 生成文件内容
    content = f"sdk.dir={sdk_str}"

    # 写入文件
    local_props_path = project_abs / "local.properties"
    with open(local_props_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 已生成 local.properties")
    print(f"📁 SDK 路径: {sdk_abs}")
    print(f"📁 项目路径: {project_abs}")
    print(f"📄 文件位置: {local_props_path}")

    return True

def build(path: str, command: str) -> bool:
    """
    实时输出日志的编译
    """
    try:
        # 切换到项目目录
        original_dir = os.getcwd()
        os.chdir(path)

        print(f"🔧 在 {path} 执行: {command}")
        print("-" * 40)

        # 执行命令
        process = subprocess.Popen(
            f"./gradlew {command}" if os.name != 'nt' else f"gradlew.bat {command}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # 实时输出
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

        # 等待完成
        return_code = process.wait()

        print("-" * 40)
        os.chdir(original_dir)

        return return_code == 0

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def copy_files(source: str, destination: str) -> bool:
    """
    复制文件或目录

    Args:
        source: 源路径（文件或目录）
        destination: 目标路径

    Returns:
        bool: 是否复制成功
    """
    try:
        src = Path(source)
        dst = Path(destination)

        if not src.exists():
            print(f"❌ 源路径不存在: {source}")
            return False

        # 确保目标目录的父目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_file():
            # 复制文件
            shutil.copy2(src, dst)
            print(f"✅ 文件复制成功: {source} -> {destination}")
        else:
            # 复制目录
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"✅ 目录复制成功: {source} -> {destination}")

        return True
    except Exception as e:
        print(f"❌ 复制失败: {e}")
        return False


def download_file_with_progress(url, save_path):
    """
    下载文件到指定位置，显示进度
    :param url: 文件下载链接
    :param save_path: 保存的完整路径（包含文件名）
    """
    try:
        # 确保保存目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 发送请求获取文件大小
        response = requests.head(url)
        total_size = int(response.headers.get('content-length', 0))

        # 开始下载
        response = requests.get(url, stream=True)
        response.raise_for_status()

        downloaded_size = 0
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded_size += len(chunk)

                # 显示进度
                if total_size > 0:
                    percent = (downloaded_size / total_size) * 100
                    print(f"\r📥 下载进度: {percent:.1f}% ({downloaded_size}/{total_size} bytes)", end="")
                else:
                    print(f"\r📥 已下载: {downloaded_size} bytes", end="")

        print(f"\n✅ 下载完成: {save_path}")
        return True

    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return False


def extract_zip(zip_path, extract_to):
    """
    解压ZIP文件到指定位置
    :param zip_path: ZIP文件路径
    :param extract_to: 解压到的目录
    """
    try:
        # 确保解压目录存在
        os.makedirs(extract_to, exist_ok=True)

        # 解压文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        print(f"✅ 解压完成: {zip_path} -> {extract_to}")
        return True

    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return False


#python .\main.py 'C:\Users\35600\AppData\Local\Android\Sdk'
if __name__ == "__main__":
    if len(sys.argv) > 1:
        sdk_path = sys.argv[1]

    else:
        print("请提供 AndroidSDK 路径")
        sys.exit(1)

    url = "https://pan.codeocean.net/d/pan/sdk/cheese-sdk-win-x64.zip"
    save_path = "./downloads/cheese-sdk-win-x64.zip"

    if not os.path.exists(save_path):
        if download_file_with_progress(url, save_path):
            print("🎉 下载SDK模板成功！")
            extract_to = str(SDK_PATH)
            extract_zip(save_path, extract_to)
        else:
            print("💥 下载SDK模板失败！！")
            sys.exit(1)


    success = clone_git_repo(
            "https://github.com/cheese-framework/CheeseStudioCore.git",
            "./git/CheeseStudioCore"
        )
    if success:
        print("🎉 克隆完成！")
        # 示例用法
        success = build(
            "./git/CheeseStudioCore",
            "shadowJar"
        )

        if success:
            print("🎉 编译完成！")
            success = copy_files(
                "./git/CheeseStudioCore/build/libs/core.jar", str(SDK_PATH.joinpath("lib", "core.jar")) )
            if success:
                print("🎉 拷贝 core.jar 成功！")
            else:
                print("💥 拷贝 core.jar 失败！！")

        else:
            print("💥 编译失败！！")
    else:
        print("💥 克隆失败！！")

    success = clone_git_repo(
        "https://github.com/cheese-framework/Cheese.git",
        "./git/Cheese"
    )
    if success:
        print("🎉 克隆完成！")
        setup_sdk(sdk_path,"./git/Cheese")
        # 示例用法
        success = build(
            "./git/Cheese",
            "app:release:assembleRelease"
        )

        if success:
            print("🎉 编译完成！")
            success = copy_files(
                "./git/Cheese/app/release/build/outputs/apk/release/js.apk", str(SDK_PATH.joinpath("components", "project","js.apk")))
            if success:
                print("🎉 拷贝 js.apk 成功！")
            else:
                print("💥 拷贝 js.apk 失败！！")

        else:
            print("💥 编译失败！！")
    else:
        print("💥 克隆失败！！")





