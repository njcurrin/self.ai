# syntax=docker/dockerfile:1.5
#
# Multi-stage build combining llama.cpp server and axolotl fine-tuning framework
# into a single container: self-llamolotl
#

# ─── Build Arguments ────────────────────────────────────────────────────────
ARG UBUNTU_VERSION=22.04
ARG CUDA_VERSION=12.4.0
ARG CUDA_SHORT=124
ARG PYTHON_VERSION=3.11
ARG PYTORCH_VERSION=2.6.0
ARG TORCH_CUDA_ARCH_LIST="7.0 7.5 8.0 8.6 9.0+PTX"
ARG TARGETARCH=amd64

# ─── Stage 1: Build llama.cpp binaries ──────────────────────────────────────
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS llama-builder

RUN apt-get update && \
    apt-get install -y build-essential cmake python3 python3-pip git libssl-dev libgomp1 && \
    rm -rf /var/cache/apt/archives && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /llama-src
COPY self.Llama/ .

RUN cmake -B build \
      -DGGML_NATIVE=OFF \
      -DGGML_CUDA=ON \
      -DGGML_BACKEND_DL=ON \
      -DGGML_CPU_ALL_VARIANTS=ON \
      -DLLAMA_BUILD_TESTS=OFF \
      -DCMAKE_EXE_LINKER_FLAGS=-Wl,--allow-shlib-undefined \
      . && \
    cmake --build build --config Release -j$(nproc)

RUN mkdir -p /app/lib && \
    find build -name "*.so*" -exec cp -P {} /app/lib \; && \
    cp build/bin/llama-server /app/llama-server

# ─── Stage 2: Build axolotl Python environment ──────────────────────────────
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS axolotl-builder

ARG PYTORCH_VERSION
ARG CUDA_SHORT
ARG TORCH_CUDA_ARCH_LIST
ARG TARGETARCH

ENV TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}
ENV PYTORCH_VERSION=${PYTORCH_VERSION}
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends --allow-change-held-packages \
        python3.11 python3.11-venv python3-pip git build-essential ninja-build \
        cmake libaio-dev pkg-config vim curl nano libnccl2 libnccl-dev rsync \
        ibverbs-providers ibverbs-utils infiniband-diags \
        librdmacm-dev librdmacm1 rdmacm-utils && \
    rm -rf /var/cache/apt/archives && \
    rm -rf /var/lib/apt/lists/*

# Create Python venv
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /workspace

# Upgrade pip and install PyTorch with CUDA 12.4 wheels
RUN pip install --upgrade pip packaging==26.0 setuptools==75.8.0 wheel psutil && \
    pip install --no-cache-dir \
        torch==${PYTORCH_VERSION}+cu${CUDA_SHORT} torchvision \
        --index-url https://download.pytorch.org/whl/cu${CUDA_SHORT} && \
    pip cache purge

# causal_conv1d and mamba_ssm (optional, try prebuilt wheels first)
RUN pip install --no-cache-dir causal-conv1d mamba-ssm 2>/dev/null || \
    echo "Note: causal_conv1d/mamba_ssm prebuilt wheels not available, skipping" && \
    pip cache purge

# Install flash-attn (try pip install first, fallback to manual download)
RUN pip install --no-cache-dir flash-attn 2>/dev/null || \
    (echo "Installing flash-attn from prebuilt wheel..." && \
     PYTHON_CP="cp$(echo ${PYTHON_VERSION} | tr -d '.')" && \
     TORCH_MAJOR_MINOR="$(echo ${PYTORCH_VERSION} | grep -oP '^\d+\.\d+')" && \
     TORCH_TAG="torch${TORCH_MAJOR_MINOR}" && \
     case "$TARGETARCH" in \
         amd64) ARCH_TAG="x86_64" ;; \
         arm64) ARCH_TAG="aarch64" ;; \
     esac && \
     WHL_FILE="flash_attn-2.8.3+cu${CUDA_SHORT}${TORCH_TAG}-${PYTHON_CP}-${PYTHON_CP}-linux_${ARCH_TAG}.whl" && \
     wget -q "https://github.com/mjun0812/flash-attention-prebuild-wheels/releases/download/v0.7.16/${WHL_FILE}" 2>/dev/null && \
     pip install --no-cache-dir "${WHL_FILE}" && \
     rm -f "${WHL_FILE}") || \
    echo "Note: flash-attn not available, axolotl will use standard attention" && \
    pip cache purge

# Clone and install axolotl
RUN git clone --depth=1 https://github.com/axolotl-ai-cloud/axolotl.git /workspace/axolotl-src

WORKDIR /workspace/axolotl-src

RUN pip uninstall -y causal_conv1d || true && \
    EXTRAS="flash-attn,ring-flash-attn,ray" && \
    pip install --no-build-isolation -e .[${EXTRAS}] && \
    python scripts/unsloth_install.py | sh 2>/dev/null || true && \
    python scripts/cutcrossentropy_install.py | sh 2>/dev/null || true && \
    pip install pytest && \
    pip cache purge

# Install FastAPI and dependencies for control API
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" aiofiles && \
    pip cache purge

# Git config for shallow clones
RUN git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*" && \
    git config --get remote.origin.fetch && \
    git config --global credential.helper store

# bash completion
COPY self.axolotl/.axolotl-complete.bash /root/.axolotl-complete.bash
RUN chmod +x /root/.axolotl-complete.bash && \
    echo 'source /root/.axolotl-complete.bash' >> /root/.bashrc

# ─── Stage 3: Runtime image ────────────────────────────────────────────────
FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} AS runtime

RUN apt-get update && \
    apt-get install -y --no-install-recommends --allow-change-held-packages \
        libgomp1 curl git supervisor python3.11 \
        libnccl2 vim nano libssl-dev && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/cache/apt/archives && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* /var/tmp/*

# Create supervisor log directory
RUN mkdir -p /var/log/supervisor

# llama.cpp artifacts from builder
COPY --from=llama-builder /app/lib/ /app/lib/
COPY --from=llama-builder /app/llama-server /app/llama-server

# axolotl Python venv and source tree from builder
COPY --from=axolotl-builder /opt/venv /opt/venv
COPY --from=axolotl-builder /workspace/axolotl-src /workspace/axolotl-src

ENV PATH="/opt/venv/bin:${PATH}"
ENV LLAMA_ARG_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# supervisord configuration
COPY self.llamolotl/supervisord.conf /etc/supervisor/conf.d/llamolotl.conf

# entrypoint script
COPY self.llamolotl/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# FastAPI control server
COPY self.llamolotl/api/ /workspace/axolotl-src/api/

EXPOSE 8093

WORKDIR /workspace/axolotl-src

# Health check for llama-server
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
