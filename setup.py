from setuptools import find_packages
from setuptools import setup
import torch.cuda as cuda
from torch.utils.cpp_extension import BuildExtension
import os
from typing import List


def get_cpp_files(root_path: str, exceptions: List[str]) -> List[str]:
    full_list = os.listdir(root_path)
    res_list = []
    for filename in full_list:
        if (filename.endswith(".cpp") or filename.endswith(".cu")) and not (filename in exceptions):
            res_list.append(os.path.join(root_path, filename))
    return res_list


requirements = ["torch"]

ext_modules = []
cuda_available = cuda.is_available()
if cuda_available:
    print("\033[92mCUDA found on this device, installing matterhorn CUDA extensions.\033[0m")
    from torch.utils.cpp_extension import CUDAExtension
    files = get_cpp_files(os.path.join(os.path.abspath("."), "matterhorn_cuda_extensions"), ["base.cpp", "base.cu"])
    print("Will compile " + ", ".join(files))
    ext_modules.append(CUDAExtension(
        "matterhorn_cuda_extensions",
        files,
        extra_compile_args = {
            "cxx": ["-g", "-w"],
            "nvcc": ["-O2"]
        }
    ))
else:
    print("\033[93mCUDA not found on this device. If you have NVIDIA's GPU, please install CUDA and try again later, or manually install Matterhorn CUDA extensions.\033[0m")
cpp_available = not os.system("g++ --version")
if cpp_available:
    print("\033[92mg++ found on this device, installing matterhorn CPP extensions.\033[0m")
    from torch.utils.cpp_extension import CppExtension
    files = get_cpp_files(os.path.join(os.path.abspath("."), "matterhorn_cpp_extensions"), ["base.cpp"])
    print("Will compile " + ", ".join(files))
    ext_modules.append(CppExtension(
        "matterhorn_cpp_extensions",
        files,
        extra_compile_args = {
            "cxx": ["-g", "-w"]
        }
    ))
else:
    print("\033[93mg++ not found on this device. Please install g++ and try again later, or manually install Matterhorn CPP extensions.\033[0m")
cmdclass = None
if cuda_available or cpp_available:
    cmdclass = {
        "build_ext": BuildExtension
    }

with open(os.path.join(os.path.abspath("."), "requirements.txt"), "r", encoding="utf-8") as fh:
    install_requires = fh.read()


with open(os.path.join(os.path.abspath("."), "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    install_requires = install_requires,
    name = "matterhorn_pytorch",
    version = "1.0.1",
    author = "CAG, IAIR, XJTU, Xi'an, China",
    author_email = "ericwang017@stu.xjtu.edu.cn",
    description = "Matterhorn is a neo general SNN framework based on PyTorch.",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/AmperiaWang/Matterhorn",
    packages = find_packages(),
    classifiers = [
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires = '>=3.7',
    ext_modules = ext_modules,
    cmdclass = cmdclass
)