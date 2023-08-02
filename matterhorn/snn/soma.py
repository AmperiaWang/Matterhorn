import torch
import torch.nn as nn
from matterhorn.snn import functions

from typing import Callable, Union, Any, Optional


"""
脉冲神经网络神经元的胞体，一层的后半段。
由突触将来自上一层神经元的脉冲信号$O_{j}^{l-1}(t)$整合成为突触后电位$X_{i}^{l}(t)$后，在胞体中进行突触后电位的累积和发放。
"""


class UOHSkeleton(nn.Module):
    def __init__(self, tau_m: float = 1.0, u_threshold: float = 1.0, u_rest: float = 0.0, spiking_function: torch.autograd.Function = functions.heaviside_rectangular) -> None:
        """
        U-O-H三段式神经元胞体骨架，分别为：
        （1）通过历史电位$H_{i}^{l}(t)$和输入电位$X_{i}^{l}(t)$计算当前电位$U_{i}^{l}(t)$；
        （2）通过当前电位$U_{i}^{l}(t)$计算当前脉冲$O_{i}^{l}(t)$；
        （3）通过当前电位$U_{i}^{l}(t-1)$与当前脉冲$O_{i}^{l}(t-1)$计算下一时刻的历史电位$H_{i}^{l}(t)$。
        @params:
            tau_m: float 膜时间常数$τ_{m}$
            u_threshold: float 阈电位$u_{th}$
            u_rest: float 静息电位$u_{rest}$
            spiking_function: torch.autograd.Function 计算脉冲时所使用的阶跃函数
        """
        super().__init__()
        assert callable(spiking_function) and isinstance(spiking_function(), torch.autograd.Function), "Spiking function must be a function that can be calculate gratitude"
        assert tau_m != 0.0, "Can't let membrane time constant tau_m be zero."
        self.tau_m = tau_m
        self.u_threshold = u_threshold
        self.u_rest = u_rest
        self.spiking_function = spiking_function()
        self.reset()
    

    def reset(self):
        """
        重置整个神经元
        """
        self.u = self.u_rest

    
    def detach(self):
        """
        将历史电位从计算图中分离，以停止在时间上进行反向传播
        """
        if isinstance(self.u, torch.Tensor):
            self.u = self.u.detach()


    def calc_potential(self, h: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        """
        通过历史电位$H_{i}^{l}(t)$和输入电位$X_{i}^{l}(t)$计算当前电位$U_{i}^{l}(t)$。
        @params:
            h: torch.Tensor 历史电位$H_{i}^{l}(t)$
            x: torch.Tensor 输入电位$X_{i}^{l}(t)$
        @return:
            u: torch.Tensor 当前电位$U_{i}^{l}(t)$
        """
        return h + (1. / self.tau_m) * x
    

    def calc_spike(self, u: torch.Tensor) -> torch.Tensor:
        """
        通过当前电位$U_{i}^{l}(t)$计算当前脉冲$O_{i}^{l}(t)$。
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t)$
        @return:
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t)$
        """
        return self.spiking_function.apply(u - self.u_threshold)
    

    def calc_history(self, u: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        """
        通过当前电位$U_{i}^{l}(t-1)$与当前脉冲$O_{i}^{l}(t-1)$计算下一时刻的历史电位$H_{i}^{l}(t)$。
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t-1)$
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t-1)$
        @return:
            h: torch.Tensor 下一时刻的历史电位$H_{i}^{l}(t)$
        """
        raise NotImplementedError
    

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播函数
        @params:
            x: torch.Tensor 来自突触的输入电位$X_{i}^{l}(t)$
        @return:
            o: torch.Tensor 胞体当前的输出脉冲$O_{i}^{l}(t)$
        """
        self.u = self.calc_potential(self.u, x)
        o = self.calc_spike(self.u)
        self.u = self.calc_history(self.u, o)
        return o


class RORSkeleton(nn.Module):
    def __init__(self, u_threshold: float = 1.0, spiking_function: torch.autograd.Function = functions.heaviside_rectangular) -> None:
        """
        R-O-R三段式神经元胞体骨架，分别为：
        （1）通过上一时刻的电位$U_{i}^{l}(t-1)$和当前时刻的输入电位$X_{i}^{l}(t)$计算电位导数$dU/dt=U_{i}^{l}(t)-U_{i}^{l}(t-1)$，进而获得当前电位$U_{i}^{l}(t)$；
        （2）通过当前电位$U_{i}^{l}(t)$计算当前脉冲$O_{i}^{l}(t)$；
        （3）通过当前脉冲$O_{i}^{l}(t)$重置当前电位$U_{i}^{l}(t)$。
        @params:
            spiking_function: torch.autograd.Function 计算脉冲时所使用的阶跃函数
        """
        super().__init__()
        assert callable(spiking_function) and isinstance(spiking_function(), torch.autograd.Function), "Spiking function must be a function that can be calculate gratitude"
        self.u_threshold = u_threshold
        self.spiking_function = spiking_function()
        self.reset()
    

    def reset(self):
        """
        重置整个神经元
        """
        self.u = self.u_rest

    
    def detach(self):
        """
        将历史电位从计算图中分离，以停止在时间上进行反向传播
        """
        if isinstance(self.u, torch.Tensor):
            self.u = self.u.detach()


    def response_function(self, u: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        """
        通过上一时刻的电位$U_{i}^{l}(t-1)$和当前时刻的输入电位$X_{i}^{l}(t)$计算电位导数$dU/dt=U_{i}^{l}(t)-U_{i}^{l}(t-1)$，进而获得当前电位$U_{i}^{l}(t)$。
        @params:
            u: torch.Tensor 上一时刻的电位$U_{i}^{l}(t-1)$
            x: torch.Tensor 输入电位$X_{i}^{l}(t)$
        @return:
            du: torch.Tensor 电位导数$dU/dt$
        """
        du = (1. / 2.) * (-u + x)
        u = u + du
        return u


    def reset_function(self, u: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        """
        通过当前脉冲$O_{i}^{l}(t)$重置当前电位$U_{i}^{l}(t)$。
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t-1)$
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t-1)$
        @return:
            u: torch.Tensor 经过重置之后的当前电位$U_{i}^{l}(t-1)$
        """
        u = u * (1. - o)
        return u
    

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播函数
        @params:
            x: torch.Tensor 来自突触的输入电位$X_{i}^{l}(t)$
        @return:
            o: torch.Tensor 胞体当前的输出脉冲$O_{i}^{l}(t)$
        """
        self.u = self.response_function(self.u, x)
        o = self.spiking_function(self.u)
        self.u = self.reset_function(self.u, o)
        return o
    

class IF(UOHSkeleton):
    def __init__(self, u_threshold: float = 1.0, u_rest: float = 0.0, spiking_function: torch.autograd.Function = functions.heaviside_rectangular) -> None:
        """
        Integrate-and-Fire(IF)神经元。
        无泄漏过程，一阶电位变换公式为：
        $$\frac{du}{dt}=RI$$
        @params:
            u_threshold: float 阈电位$u_{th}$
            u_rest: float 静息电位$u_{rest}$
            spiking_function: torch.autograd.Function 计算脉冲时所使用的阶跃函数
        """
        super().__init__(
            tau_m = 1.0,
            u_threshold = u_threshold,
            u_rest = u_rest,
            spiking_function = spiking_function
        )
    

    def calc_history(self, u: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        """
        通过当前电位$U_{i}^{l}(t-1)$与当前脉冲$O_{i}^{l}(t-1)$计算下一时刻的历史电位$H_{i}^{l}(t)$。
        使用离散代换推得历史电位公式为：
        $$H_{i}^{l}(t)=U_{i}^{l}(t-1)$$
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t-1)$
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t-1)$
        @return:
            h: torch.Tensor 下一时刻的历史电位$H_{i}^{l}(t)$
        """
        h = u
        h = h * (1. - o) + self.u_rest * o
        return h


class LIF(UOHSkeleton):
    def __init__(self, tau_m: float = 2.0, u_threshold: float = 1.0, u_rest: float = 0.0, spiking_function: torch.autograd.Function = functions.heaviside_rectangular) -> None:
        """
        Leaky-Integrate-and-Fire(LIF)神经元。
        一阶电位变换公式为：
        $$τ\frac{du}{dt}=-(u-u_{rest})+RI$$
        @params:
            tau_m: float 膜时间常数$τ_{m}$
            u_threshold: float 阈电位$u_{th}$
            u_rest: float 静息电位$u_{rest}$
            spiking_function: torch.autograd.Function 计算脉冲时所使用的阶跃函数
        """
        super().__init__(
            tau_m = tau_m,
            u_threshold = u_threshold,
            u_rest = u_rest,
            spiking_function = spiking_function
        )
    
    
    def calc_history(self, u: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        """
        通过当前电位$U_{i}^{l}(t-1)$与当前脉冲$O_{i}^{l}(t-1)$计算下一时刻的历史电位$H_{i}^{l}(t)$。
        使用离散代换推得历史电位公式为：
        $$H_{i}^{l}(t)=(1-\frac{1}{τ})U_{i}^{l}(t-1)+\frac{1}{τ}u_{rest}$$
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t-1)$
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t-1)$
        @return:
            h: torch.Tensor 下一时刻的历史电位$H_{i}^{l}(t)$
        """
        h = (1. - 1. / self.tau_m) * u + (1. / self.tau_m) * self.u_rest
        h = h * (1. - o) + self.u_rest * o
        return h


class QIF(UOHSkeleton):
    def __init__(self, tau_m: float = 2.0, u_threshold: float = 1.0, u_rest: float = 0.0, u_c: float = 0.8, a_0: float = 1.0, spiking_function: torch.autograd.Function = functions.heaviside_rectangular) -> None:
        """
        Quadratic Integrate-and-Fire(QIF)神经元。
        一阶电位变换公式为：
        $$τ\frac{du}{dt}=a_{0}(u-u_{rest})(u-u_{c})+RI$$
        @params:
            tau_m: float 膜时间常数$τ_{m}$
            u_threshold: float 阈电位$u_{th}$
            u_rest: float 静息电位$u_{rest}$
            u_c: float 参数$u_{c}$
            a_0: float 参数$a_{0}$
            spiking_function: torch.autograd.Function 计算脉冲时所使用的阶跃函数
        """
        super().__init__(
            tau_m = tau_m,
            u_threshold = u_threshold,
            u_rest = u_rest,
            spiking_function = spiking_function
        )
        self.a_0 = a_0
        self.u_c = u_c
    
    
    def calc_history(self, u: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        """
        通过当前电位$U_{i}^{l}(t-1)$与当前脉冲$O_{i}^{l}(t-1)$计算下一时刻的历史电位$H_{i}^{l}(t)$。
        使用离散代换推得历史电位公式为：
        $$H_{i}^{l}(t)=U_{i}^{l}(t-1)-\frac{a_{0}}{τ}[U_{i}^{l}(t-1)-u_{rest}][U_{i}^{l}(t-1)-u_{c}]$$
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t-1)$
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t-1)$
        @return:
            h: torch.Tensor 下一时刻的历史电位$H_{i}^{l}(t)$
        """
        h = u - (self.a_0 / self.tau_m) * (u - self.u_rest) * (u - self.u_c)
        h = h * (1. - o) + self.u_rest * o
        return h


class EIF(UOHSkeleton):
    def __init__(self, tau_m: float = 2.0, u_threshold: float = 1.0, u_rest: float = 0.0, u_t: float = 8.0, delta_t: float = 1.0, spiking_function: torch.autograd.Function = functions.heaviside_rectangular) -> None:
        """
        Exponential Integrate-and-Fire(EIF)神经元。
        一阶电位变换公式为：
        $$τ\frac{du}{dt}=-(u-u_{rest})+Δ_{T}e^{\frac{u-u_{T}}{Δ_{T}}}+RI$$
        @params:
            tau_m: float 膜时间常数$τ_{m}$
            u_threshold: float 阈电位$u_{th}$
            u_rest: float 静息电位$u_{rest}$
            u_t: float 参数$u_{T}$
            delta_t: float 参数$Δ_{T}$
            spiking_function: torch.autograd.Function 计算脉冲时所使用的阶跃函数
        """
        super().__init__(
            tau_m = tau_m,
            u_threshold = u_threshold,
            u_rest = u_rest,
            spiking_function = spiking_function
        )
        self.delta_t = delta_t
        self.u_t = u_t
    
    
    def calc_history(self, u: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        """
        通过当前电位$U_{i}^{l}(t-1)$与当前脉冲$O_{i}^{l}(t-1)$计算下一时刻的历史电位$H_{i}^{l}(t)$。
        使用离散代换推得历史电位公式为：
        $$H_{i}^{l}(t)=(1-\frac{1}{τ})U_{i}^{l}(t-1)+\frac{1}{τ}u_{rest}+\frac{Δ_{T}}{τ}e^{\frac{U_{i}^{l}(t-1)-u_{T}}{Δ_{T}}}$$
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t-1)$
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t-1)$
        @return:
            h: torch.Tensor 下一时刻的历史电位$H_{i}^{l}(t)$
        """
        h = (1. - 1. / self.tau_m) * u + (1. / self.tau_m) * self.u_rest + (self.delta_t / self.tau_m) * torch.exp((u - self.u_t) / self.delta_t)
        h = h * (1. - o) + self.u_rest * o
        return h


class Izhikevich(UOHSkeleton):
    def __init__(self, a: float = 1.0, b: float = 1.0, u_threshold: float = 1.0, spiking_function: torch.autograd.Function = functions.heaviside_rectangular) -> None:
        """
        Izhikevich神经元。
        一阶电位变换公式为：
        $$\frac{du}{dt}=0.04u^{2}+5u+140-w+I$$
        $$\frac{dw}{dt}=a(bu-w)$$
        @params:
            tau_m: float 膜时间常数$τ_{m}$
            u_threshold: float 阈电位$u_{th}$
            u_rest: float 静息电位$u_{rest}$
            u_t: float 参数$u_{T}$
            delta_t: float 参数$Δ_{T}$
            spiking_function: torch.autograd.Function 计算脉冲时所使用的阶跃函数
        """
        super().__init__(
            tau_m = 1.0,
            u_threshold = u_threshold,
            u_rest = 0.0,
            spiking_function = spiking_function
        )
        self.a = a
        self.b = b


    def reset(self):
        """
        重置整个神经元
        """
        self.u = 0.0
        self.w = 0.0

    
    def detach(self):
        """
        将历史电位从计算图中分离，以停止在时间上进行反向传播
        """
        if isinstance(self.u, torch.Tensor):
            self.u = self.u.detach()
        if isinstance(self.w, torch.Tensor):
            self.w = self.w.detach()


    def calc_potential(self, h: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        """
        通过历史电位$H_{i}^{l}(t)$和输入电位$X_{i}^{l}(t)$计算当前电位$U_{i}^{l}(t)$。
        @params:
            h: torch.Tensor 历史电位$H_{i}^{l}(t)$
            x: torch.Tensor 输入电位$X_{i}^{l}(t)$
        @return:
            u: torch.Tensor 当前电位$U_{i}^{l}(t)$
        """
        return h + x
    

    def calc_history(self, u: torch.Tensor, o: torch.Tensor) -> torch.Tensor:
        """
        通过当前电位$U_{i}^{l}(t-1)$与当前脉冲$O_{i}^{l}(t-1)$计算下一时刻的历史电位$H_{i}^{l}(t)$。
        使用离散代换推得历史电位公式为：
        $$H_{i}^{l}(t)=0.04[U_{i}^{l}(t-1)]^{2}+6U_{i}^{l}(t-1)+140-W_{i}^{l}(t-1)$$
        $$W_{i}^{l}(t)=abU_{i}^{l}(t-1)-(a-1)W_{i}^{l}(t-1)$$
        @params:
            u: torch.Tensor 当前电位$U_{i}^{l}(t-1)$
            o: torch.Tensor 当前脉冲$O_{i}^{l}(t-1)$
        @return:
            h: torch.Tensor 下一时刻的历史电位$H_{i}^{l}(t)$
        """
        h = 0.04 * u * u + 6 * u + 140 - self.w
        self.w = self.a * self.b * u - (self.a - 1) * self.w
        return h