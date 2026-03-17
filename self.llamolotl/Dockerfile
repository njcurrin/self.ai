# syntax=docker/dockerfile:1.5
#
# Multi-stage build combining llama.cpp server and axolotl fine-tuning framework
# into a single container: self-llamolotl
#

# ─── Build Arguments ────────────────────────────────────────────────────────
ARG UBUNTU_VERSION=22.04
ARG CUDA_VERSION=13.1.0
ARG CUDA_BUILD_VERSION=12.8.0
ARG CUDA_SHORT=128
ARG PYTHON_VERSION=3.11
ARG PYTORCH_VERSION=2.10.0
ARG TORCH_CUDA_ARCH_LIST="8.9+PTX"
ARG TARGETARCH=amd64

# ─── Stage 1: Build llama.cpp binaries ──────────────────────────────────────
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS llama-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential cmake git libssl-dev libgomp1 && \
    rm -rf /var/cache/apt/archives && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /llama-src
COPY self.Llama/ .

RUN export LDFLAGS="-L/usr/local/cuda/lib64/stubs $LDFLAGS" && \
    cmake -B build \
      -DGGML_NATIVE=OFF \
      -DGGML_CUDA=ON \
      -DLLAMA_BUILD_TESTS=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_EXE_LINKER_FLAGS="-L/usr/local/cuda/lib64/stubs -Wl,--allow-shlib-undefined" \
      -DCMAKE_SHARED_LINKER_FLAGS="-L/usr/local/cuda/lib64/stubs -Wl,--allow-shlib-undefined" \
      . && \
    cmake --build build --config Release -j$(nproc)

RUN mkdir -p /app && \
    cp build/bin/llama-server /app/llama-server && \
    cp build/bin/llama-bench /app/llama-bench && \
    find build/bin -name "*.so*" -exec cp -P {} /app/ \;

# ─── Stage 2: Build axolotl Python environment ──────────────────────────────
# Uses CUDA_BUILD_VERSION (12.8) to match PyTorch cu128 wheels for native
# extension compilation (flash-attn, etc). The built venv is forward-compatible
# and runs on the CUDA 13.1 runtime without issues.
FROM nvidia/cuda:${CUDA_BUILD_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS axolotl-builder

ARG PYTORCH_VERSION
ARG CUDA_SHORT
ARG TORCH_CUDA_ARCH_LIST
ARG TARGETARCH

ENV TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}
ENV PYTORCH_VERSION=${PYTORCH_VERSION}
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends --allow-change-held-packages \
        python3.11 python3.11-dev python3.11-venv python3-pip git build-essential ninja-build \
        cmake libaio-dev pkg-config vim curl nano libnccl2 libnccl-dev rsync \
        ibverbs-providers ibverbs-utils infiniband-diags \
        librdmacm-dev librdmacm1 rdmacm-utils && \
    rm -rf /var/cache/apt/archives && \
    rm -rf /var/lib/apt/lists/*

# Create Python venv
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
# Limit parallel CUDA kernel compilations to stay within ~100GB memory budget
# Peak memory ≈ MAX_JOBS × NVCC_THREADS × 5GB = 8 × 2 × 5 = 80GB
ENV MAX_JOBS="8"
ENV NVCC_THREADS="2"
ENV CMAKE_BUILD_PARALLEL_LEVEL="8"

WORKDIR /workspace

# Upgrade pip and install PyTorch with CUDA wheels
RUN pip install --upgrade pip packaging setuptools wheel psutil && \
    pip install --no-cache-dir \
        torch==${PYTORCH_VERSION}+cu${CUDA_SHORT} torchvision \
        --index-url https://download.pytorch.org/whl/cu${CUDA_SHORT} && \
    pip cache purge

# causal_conv1d and mamba_ssm (optional, try prebuilt wheels first)
RUN pip install --no-cache-dir causal-conv1d mamba-ssm 2>/dev/null || \
    echo "Note: causal_conv1d/mamba_ssm prebuilt wheels not available, skipping" && \
    pip cache purge

# Debug: log parallelism settings and CPU count
RUN echo "=== BUILD PARALLELISM ===" && \
    echo "MAX_JOBS=$MAX_JOBS" && \
    echo "CMAKE_BUILD_PARALLEL_LEVEL=$CMAKE_BUILD_PARALLEL_LEVEL" && \
    echo "nproc=$(nproc)" && \
    python -c "import os; print(f'Python os.cpu_count()={os.cpu_count()}'); print(f'MAX_JOBS from env={os.environ.get(\"MAX_JOBS\", \"NOT SET\")}')"

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

# Remove causal_conv1d if previously installed (conflicts with axolotl's pinned version)
RUN pip uninstall -y causal_conv1d 2>/dev/null; true

# Install axolotl with extras — this MUST succeed
# MAX_JOBS limits parallel CUDA kernel compilations (~3-4GB each) to stay within memory budget
RUN pip install --no-build-isolation -e ".[flash-attn,ring-flash-attn,ray]" && \
    pip cache purge

# Optional post-install scripts (non-fatal)
RUN python scripts/unsloth_install.py | sh 2>/dev/null; true
RUN python scripts/cutcrossentropy_install.py | sh 2>/dev/null; true

RUN pip install --no-cache-dir pytest && pip cache purge

# Patch: disable @torch.jit.script in trainer.py — the create_weighted_mask JIT
# compilation segfaults when 200+ C extension modules are loaded (PyTorch JIT bug
# triggered by transitive imports from axolotl.utils.config pulling in sklearn,
# scipy, pyarrow, numba, etc). The functions work identically without JIT.
RUN sed -i 's/^@torch\.jit\.script$/# @torch.jit.script  # disabled: JIT segfault with extension module interaction/' \
    /workspace/axolotl-src/src/axolotl/utils/trainer.py

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
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS runtime

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl supervisor python3.11 vim nano && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/cache/apt/archives && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* /var/tmp/*

# Create supervisor log directory
RUN mkdir -p /var/log/supervisor

# llama.cpp artifacts from builder (binaries + shared libraries)
COPY --from=llama-builder /app/ /app/

# axolotl Python venv and source tree from builder
COPY --from=axolotl-builder /opt/venv /opt/venv
COPY --from=axolotl-builder /workspace/axolotl-src /workspace/axolotl-src

ENV PATH="/app:/opt/venv/bin:${PATH}"
ENV LD_LIBRARY_PATH=/app:/usr/local/cuda/lib64
ENV LLAMA_ARG_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/llamolotl.conf

# entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# FastAPI control server
COPY api/ /workspace/axolotl-src/api/

EXPOSE 8093

WORKDIR /workspace/axolotl-src

# Health check for llama-server
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
