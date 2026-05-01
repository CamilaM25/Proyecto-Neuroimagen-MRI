#!/bin/bash
# ==============================================================================
# Script para ejecutar fMRIPrep optimizado en todos los sujetos de un dataset BIDS
#
# Uso:
#   ./run_fmriprep_all_optimized.sh <BIDS_DIR> <OUTPUT_DIR> <0|1: Sin o con FreeSurfer>
#
# Parámetros:
#   <BIDS_DIR>    → Ruta al dataset BIDS
#   <OUTPUT_DIR>  → Ruta donde se guardarán los resultados de fMRIPrep
#   <0|1>         → 0 = sin FreeSurfer | 1 = con FreeSurfer
#
# Ejemplo:
#   ./run_fmriprep_all_optimized.sh /data/bids /data/fmriprep_out 0
#
# Requisitos:
#   - Docker instalado y funcionando
#   - Dataset BIDS válido
#   - Archivo de licencia de FreeSurfer disponible (aunque no se use)
# ==============================================================================

# ==== CONFIGURACIÓN ====
BIDS_DIR="$1"
OUTPUT_DIR="$2"
FS_OPTION="$3"
IMAGE="nipreps/fmriprep:latest"
WORK_DIR="/home/neuro-admin/Documents/database/work"
LICENSE_FILE="/home/neuro-admin/freesurfer/license.txt"
# =======================

# ==== OPTIMIZACIÓN AUTOMÁTICA ====
# Número de CPUs
N_CPUS=$(nproc)

# Memoria total en MB (90% del total disponible)
TOTAL_MEM_MB=$(free -m | awk '/^Mem:/ {print $2}')
MEM_MB=$(echo "$TOTAL_MEM_MB * 0.9 / 1" | bc) # 90% de la memoria

# Hilos por proceso OpenMP: total de CPUs
OMP_NTHREADS="$N_CPUS"
# ================================

# Obtener lista de sujetos (quita el prefijo sub- para pasar solo el ID)
SUBJECTS=$(ls "$BIDS_DIR" | grep -E '^sub-' | sed 's/sub-//')

# Recorrer y correr fMRIPrep por cada sujeto
for subj in $SUBJECTS; do
  echo ">>> Procesando sujeto: sub-${subj} <<<"

  # Parámetros de optimización
  PERF_OPTS="--n_cpus $N_CPUS --omp-nthreads $OMP_NTHREADS --mem_mb $MEM_MB --low-mem"

  if [ "$FS_OPTION" == 0 ]; then
    # Sin reconstrucción cortical (más rápido, menos outputs anatómicos)
    docker run -it --rm \
      -v "$BIDS_DIR":/data:ro \
      -v "$OUTPUT_DIR":/out \
      -v "$WORK_DIR":/work \
      -v "$LICENSE_FILE":/opt/freesurfer/license.txt:ro \
      $IMAGE \
      /data /out participant \
      --participant-label $subj \
      --fs-no-reconall \
      -w /work \
      $PERF_OPTS
  else
    # Con reconstrucción cortical usando FreeSurfer
    docker run -it --rm \
      -v "$BIDS_DIR":/data:ro \
      -v "$OUTPUT_DIR":/out \
      -v "$WORK_DIR":/work \
      -v "$LICENSE_FILE":/opt/freesurfer/license.txt:ro \
      $IMAGE \
      /data /out participant \
      --participant-label $subj \
      -w /work \
      $PERF_OPTS
  fi

  echo "==== Terminado sujeto: sub-${subj} ===="
  echo
done

echo ">>> Todos los sujetos procesados."