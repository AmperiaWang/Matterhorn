#include "soma.h"
#include <ATen/ATen.h>
#include <iostream>
#include <cmath>
#include <vector>

void fp_response_lif(at::Tensor u,
                    at::Tensor x,
                    at::Tensor h,
                    at::Tensor tau_m,
                    float u_rest) {
    float tau_m_val = tau_m.data<float>()[0];
    at::Tensor du = (1.0 / tau_m_val) * (-(h - u_rest) + x);
    u += h + du;
}

void fp_spiking_heaviside(at::Tensor o, at::Tensor u, float u_threshold) {
    o += (u >= u_threshold);
}

void fp_reset_hard(at::Tensor h, at::Tensor u, at::Tensor o, float u_rest) {
    h += u * (1.0 - o) + u_rest * o;
}

void bp_response_lif(at::Tensor grad_u,
                    at::Tensor grad_x,
                    at::Tensor grad_h,
                    at::Tensor grad_tau_m,
                    at::Tensor u,
                    at::Tensor x,
                    at::Tensor h,
                    at::Tensor tau_m,
                    float u_rest) {
    /*
    $$U_{i}^{l}(t)=H_{i}^{l}(t-1)+\frac{1}{τ_{m}}[-[H_{i}^{l}(t-1)-u_{rest}]+X_{i}^{l}(t)]$$
    =>
    $$\frac{\partial U_{i}^{l}(t)}{\partial H_{i}^{l}(t-1)}=1-\frac{1}{τ_{m}}$$
    $$\frac{\partial U_{i}^{l}(t)}{\partial X_{i}^{l}(t)}=\frac{1}{τ_{m}}$$
    $$\frac{\partial U_{i}^{l}(t)}{\partial τ_{m}}=-\frac{1}{τ_{m}^{2}}[-[H_{i}^{l}(t-1)-u_{rest}]+X_{i}^{l}(t)]$$
    */
    float tau_m_val = tau_m.data<float>()[0];
    grad_x += grad_u * (1.0 / tau_m_val);
    grad_h += grad_u * (1.0 - (1.0 / tau_m_val));
    grad_tau_m += grad_u * (-(1 / tau_m_val / tau_m_val) * (-(h - u_rest) + x));
}

void bp_spiking_rectangular(at::Tensor grad_o,
                           at::Tensor grad_u,
                           at::Tensor o,
                           at::Tensor u,
                           float u_threshold) {
    /*
    $$O_{i}^{l}(t)=u[U_{i}^{l}(t)]$$
    =>
    $$\frac{\partial O_{i}^{l}(t)}{\partial U_{i}^{l}(t)}=u'$$
    */
    grad_u += grad_o * 0.5 * ((u >= u_threshold - 1) & (u <= u_threshold + 1));
}

void bp_reset_hard(at::Tensor grad_h,
                  at::Tensor grad_u,
                  at::Tensor grad_o,
                  at::Tensor h,
                  at::Tensor u,
                  at::Tensor o,
                  float u_rest) {
    /*
    $$H_{i}^{l}(t)=U_{i}^{l}(t)[1-O_{i}^{l}(t)]+u_{rest}O_{i}^{l}(t)$$
    =>
    $$\frac{\partial H_{i}^{l}(t)}{\partial U_{i}^{l}(t)}=1-O_{i}^{l}(t)$$
    $$\frac{\partial H_{i}^{l}(t)}{\partial O_{i}^{l}(t)}=-U_{i}^{l}(t)+u_{rest}$$
    */
    grad_u += grad_h * (1 - o);
    grad_o += grad_h * (u_rest - u);
}

/*
LIF神经元的前向传播函数
@params:
    o: at::Tensor 脉冲输出o

*/
void fp_lif(at::Tensor o,
           at::Tensor u,
           at::Tensor h,
           at::Tensor x,
           int time_steps,
           at::Tensor u_init,
           at::Tensor tau_m,
           float u_rest,
           float u_threshold) {
    for (int t = 0; t < time_steps; t++) {
        fp_response_lif(u[t], x[t], t ? h[t - 1] : u_init, tau_m, u_rest);
        fp_spiking_heaviside(o[t], u[t], u_threshold);
        fp_reset_hard(h[t], u[t], o[t], u_rest);
    }
}

void bp_lif(at::Tensor grad_o,
           at::Tensor grad_u,
           at::Tensor grad_h,
           at::Tensor grad_x,
           at::Tensor grad_u_init,
           at::Tensor grad_tau_m,
           int time_steps,
           at::Tensor o,
           at::Tensor u,
           at::Tensor h,
           at::Tensor x,
           at::Tensor u_init,
           at::Tensor tau_m,
           float u_rest,
           float u_threshold) {
    for (int t = time_steps - 1; t >= 0; t--) {
        bp_reset_hard(grad_h[t], grad_u[t], grad_o[t], h[t], u[t], o[t],
                      u_rest);
        bp_spiking_rectangular(grad_o[t], grad_u[t], o[t], u[t], u_threshold);
        bp_response_lif(grad_u[t], grad_x[t], t ? grad_h[t - 1] : grad_u_init,
                        grad_tau_m, u[t], x[t], t ? h[t] : u_init, tau_m,
                        u_rest);
    }
}