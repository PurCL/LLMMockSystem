# install_hook.py
import os
import shutil
import glob
import sys

sp_dirs = glob.glob(".venv/lib/python*/site-packages")
if not sp_dirs:
    print("❌ Error: 找不到 .venv 文件夹。请确保你在项目根目录。")
    sys.exit(1)

site_packages = sp_dirs[0]

# 🚨 修改点 1：将拷贝目标更新为新的自动安装 Hook
for file in ["src/auto_install_hook.py", "src/llm_client.py"]:
    if not os.path.exists(file):
        print(f"❌ Error: 找不到 {file}。")
        sys.exit(1)
    shutil.copy(file, site_packages)

# 🚨 修改点 2：更新 .pth 文件名和内部触发语句
pth_path = os.path.join(site_packages, "000_auto_install.pth")
with open(pth_path, "w") as f:
    f.write("import auto_install_hook\n")

# 🚨 修改点 3：更新提示文案，反映新的“自愈”机制
print(f"✅ 成功将依赖自愈 Hook 植入到: {site_packages}")
print("====================================================")
print("🎉 安装完成！现在你可以直接激活虚拟环境并运行你的项目了：")
print("source .venv/bin/activate")
print("python -m uvicorn app.main:app")
print("====================================================")