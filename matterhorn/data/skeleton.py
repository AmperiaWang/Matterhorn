import numpy as np
import torch
from torch.utils.data import Dataset
from torchvision.datasets.utils import check_integrity
from typing import Tuple, Union, Callable, Optional
import os
import random


class EventDataset(Dataset):
    original_data_polarity_exists = False
    original_size = (1,)
    mirrors = []
    resources = []
    labels = []
    data_target = []


    def __init__(self, root: str, train: bool = True, transform: Optional[Callable] = None, target_transform: Optional[Callable] = None, download: bool = False) -> None:
        """
        原始数据后缀名为.hdf5的数据集
        @params:
            root: str 数据集的存储位置
            train: bool 是否为训练集
            transform: Callable | None 数据如何变换
            target_transform: Callable | None 标签如何变换
            download: bool 如果数据集不存在，是否应该下载
            precision: int 最终数据集的时间精度
            time_steps: int 最终的数据集总共含有多少个时间步
            length: int 最终数据集的空间精度
        """
        super().__init__()
        self.root = root
        self.transform = transform
        self.target_transform = target_transform
        self.train = train
        if download:
            self.download()
        self.pre_process()


    @property
    def raw_folder(self) -> str:
        """
        刚下载下来的数据集所存储的地方。
        @return:
            str 数据集存储位置
        """
        return os.path.join(self.root, self.__class__.__name__, "raw")


    @property
    def extracted_folder(self) -> str:
        """
        解压过后的数据集所存储的地方。
        @return:
            str 数据集存储位置
        """
        return os.path.join(self.root, self.__class__.__name__, "extracted")


    @property
    def processed_folder(self) -> str:
        """
        处理过后的数据集所存储的地方。
        @return:
            str 数据集存储位置
        """
        return os.path.join(self.root, self.__class__.__name__, "processed")


    def check_exists(self) -> bool:
        """
        检查是否存在。
        @return:
            if_exist: bool 是否存在
        """
        return all(
            check_integrity(os.path.join(self.raw_folder, filename)) for fileurl, filename, md5 in self.resources
        )


    def download(self) -> None:
        """
        下载数据集。
        """
        return


    def extract(self, data: np.ndarray, mask: int, shift: int) -> np.ndarray:
        """
        从事件数据中提取x,y,p值所用的函数。
        @params:
            data: np.ndarray 事件数据
            mask: int 对应的掩模
            shift: int 对应的偏移量
        @return:
            data: np.ndarray 处理后的数据（x,y,p）
        """
        return (data >> shift) & mask


    def load_data(self) -> np.ndarray:
        """
        加载数据集。
        @return:
            data_label: np.ndarray 数据信息，包括3列：数据集、标签、其为训练集（1）还是测试集（0）。
        """
        return None
    

    def save_event_data(self, data_idx: int, event_data: np.ndarray) -> bool:
        """
        将预处理的数据存储至文件中。
        @params:
            data_idx: int 数据序号
            event_data: np.ndarray 事件数据
        """
        event_data = self.compress_event_data(event_data)
        np.save(os.path.join(self.processed_folder, "%d.npy" % (data_idx,)), event_data)
        return True
    

    def pre_process(self) -> None:
        """
        数据的预处理，可以自定义。
        """
        if not self.check_exists():
            raise RuntimeError("Dataset not found. You can use download=True to download it")
        self.data_target = self.load_data()
        self.data_target = self.data_target[self.data_target[:, 2] == (1 if self.train else 0)][:, :2]
        self.data_target = self.data_target.tolist()
        random.shuffle(self.data_target)
    

    def compress_event_data(self, data: np.ndarray) -> np.ndarray:
        """
        压缩事件数据。
        @params:
            data: np.ndarray 未被压缩的数据
        @return:
            compressed_data: np.ndarray 已被压缩的数据
        """
        return data


    def decompress_event_data(self, data: np.ndarray) -> np.ndarray:
        """
        解压事件数据。
        @params:
            data: np.ndarray 未被解压的数据
        @return:
            decompressed_data: np.ndarray 已被解压的数据
        """
        return data


    def event_data_2_tensor(self, data: np.ndarray) -> torch.Tensor:
        """
        将缓存的numpy矩阵转为最后的PyTorch张量。
        @params:
            data: np.ndarray 数据
        @return:
            data_tensor: torch.Tensor 渲染成事件的张量
        """
        return torch.tensor(data, dtype = torch.float)


    def __len__(self) -> int:
        """
        获取数据集长度。
        @return:
            len: int 数据集长度
        """
        return len(self.data_target)
    
    
    def __getitem__(self, index: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取数据集。
        @params:
            index: int 索引
        @return:
            x: torch.Tensor 数据
            y: torch.Tensor 标签
        """
        data_idx = self.data_target[index][0]
        data = np.load(os.path.join(self.processed_folder, "%d.npy" % (data_idx,)))
        data = self.decompress_event_data(data)
        data = self.event_data_2_tensor(data)
        target = self.data_target[index][1]
        if self.transform is not None:
            data = self.transform(data)
        if self.target_transform is not None:
            target = self.target_transform(data)
        return data, target


class EventDataset1d(EventDataset):
    original_size = (1, 2, 128)


    def __init__(self, root: str, train: bool = True, transform: Optional[Callable] = None, target_transform: Optional[Callable] = None, download: bool = False, t_size: int = 128, x_size: int = 128, polarity: bool = True, clipped: Optional[Union[Tuple, float]] = None) -> None:
        self.t_size = t_size
        self.p_size = 2 if polarity else 1
        self.x_size = x_size
        if isinstance(clipped, Tuple):
            assert clipped[1] > clipped[0], "Clip end must be larger than clip start."
        self.clipped = clipped
        super().__init__(
            root = root,
            train = train,
            transform = transform,
            target_transform = target_transform,
            download = download
        )
    

    def tx_2_tensor(self, data: np.ndarray) -> torch.Tensor:
        """
        将t,x数组转为最后的PyTorch张量。
        @params:
            data: np.ndarray 数据，形状为[n, 2]
        @return:
            data_tensor: torch.Tensor 渲染成事件的张量，形状为[T, L]
        """
        res = torch.zeros(self.t_size, self.x_size, dtype = torch.float)
        if self.clipped is not None:
            if isinstance(self.clipped, int):
                data = data[data[:, 0] < self.clipped]
            elif isinstance(self.clipped, Tuple):
                data = data[(data[:, 0] >= self.clipped[0]) & (data[:, 0] < self.clipped[1])]
        data[:, 0] = np.floor(data[:, 0] * self.t_size / max(np.max(data[:, 0]) + 1, self.original_size[0]))
        data[:, 1] = np.floor(data[:, 1] * self.x_size / self.original_size[2])
        data = np.unique(data, axis = 0)
        res[data.T] = 1
        return res
    

    def tpx_2_tensor(self, data: np.ndarray) -> torch.Tensor:
        """
        将t,p,x数组转为最后的PyTorch张量。
        @params:
            data: np.ndarray 数据，形状为[n, 3]
        @return:
            data_tensor: torch.Tensor 渲染成事件的张量，形状为[T, C(P), L]
        """
        res = torch.zeros(self.t_size, self.p_size, self.x_size, dtype = torch.float)
        if self.clipped is not None:
            if isinstance(self.clipped, int):
                data = data[data[:, 0] < self.clipped]
            elif isinstance(self.clipped, Tuple):
                data = data[(data[:, 0] >= self.clipped[0]) & (data[:, 0] < self.clipped[1])]
        data[:, 0] = np.floor(data[:, 0] * self.t_size / max(np.max(data[:, 0]) + 1, self.original_size[0]))
        data[:, 1] = np.floor(data[:, 1] * self.p_size / self.original_size[1])
        data[:, 2] = np.floor(data[:, 2] * self.x_size / self.original_size[2])
        data = np.unique(data, axis = 0)
        res[data.T] = 1
        return res


    def event_data_2_tensor(self, data: np.ndarray) -> torch.Tensor:
        """
        将缓存的numpy矩阵转为最后的PyTorch张量。
        @params:
            data: np.ndarray 数据
        @return:
            data_tensor: torch.Tensor 渲染成事件的张量
        """
        if self.original_data_polarity_exists:
            return self.tpx_2_tensor(data)
        return self.tx_2_tensor(data)


class EventDataset2d(EventDataset):
    original_size = (1, 2, 128, 128)


    def __init__(self, root: str, train: bool = True, transform: Optional[Callable] = None, target_transform: Optional[Callable] = None, download: bool = False, t_size: int = 128, y_size: int = 128, x_size: int = 128, polarity: bool = True, clipped: Optional[Union[Tuple, float]] = None) -> None:
        self.t_size = t_size
        self.p_size = 2 if polarity else 1
        self.y_size = y_size
        self.x_size = x_size
        if isinstance(clipped, Tuple):
            assert clipped[1] > clipped[0], "Clip end must be larger than clip start."
        self.clipped = clipped
        super().__init__(
            root = root,
            train = train,
            transform = transform,
            target_transform = target_transform,
            download = download
        )


    def tyx_2_tensor(self, data: np.ndarray) -> torch.Tensor:
        """
        将t,y,x数组转为最后的PyTorch张量。
        @params:
            data: np.ndarray 数据，形状为[n, 3]
        @return:
            data_tensor: torch.Tensor 渲染成事件的张量，形状为[T, H, W]
        """
        res = torch.zeros(self.t_size, self.y_size, self.x_size, dtype = torch.float)
        if self.clipped is not None:
            if isinstance(self.clipped, int):
                data = data[data[:, 0] < self.clipped]
            elif isinstance(self.clipped, Tuple):
                data = data[(data[:, 0] >= self.clipped[0]) & (data[:, 0] < self.clipped[1])]
        data[:, 0] = np.floor(data[:, 0] * self.t_size / max(np.max(data[:, 0]) + 1, self.original_size[0]))
        data[:, 1] = np.floor(data[:, 1] * self.y_size / self.original_size[2])
        data[:, 2] = np.floor(data[:, 2] * self.x_size / self.original_size[3])
        data = np.unique(data, axis = 0)
        res[data.T] = 1
        return res


    def tpyx_2_tensor(self, data: np.ndarray) -> torch.Tensor:
        """
        将t,p,y,x数组转为最后的PyTorch张量。
        @params:
            data: np.ndarray 数据，形状为[n, 4]
        @return:
            data_tensor: torch.Tensor 渲染成事件的张量，形状为[T, C(P), H, W]
        """
        res = torch.zeros(self.t_size, self.p_size, self.y_size, self.x_size, dtype = torch.float)
        if self.clipped is not None:
            if isinstance(self.clipped, int):
                data = data[data[:, 0] < self.clipped]
            elif isinstance(self.clipped, Tuple):
                data = data[(data[:, 0] >= self.clipped[0]) & (data[:, 0] < self.clipped[1])]
        data[:, 0] = np.floor(data[:, 0] * self.t_size / max(np.max(data[:, 0]) + 1, self.original_size[0]))
        data[:, 1] = np.floor(data[:, 1] * self.p_size / self.original_size[1])
        data[:, 2] = np.floor(data[:, 2] * self.y_size / self.original_size[2])
        data[:, 3] = np.floor(data[:, 3] * self.x_size / self.original_size[3])
        data = np.unique(data, axis = 0)
        res[data.T] = 1
        return res


    def event_data_2_tensor(self, data: np.ndarray) -> torch.Tensor:
        """
        将缓存的numpy矩阵转为最后的PyTorch张量。
        @params:
            data: np.ndarray 数据
        @return:
            data_tensor: torch.Tensor 渲染成事件的张量
        """
        if self.original_data_polarity_exists:
            return self.tpyx_2_tensor(data)
        return self.tyx_2_tensor(data)