# Proyecto Neuroimagen MRI 20261

Pipeline de análisis de conectividad funcional motora en pacientes post-ACV, utilizando datos de fMRI pre y post rehabilitación.

---

## Dataset

| Campo | Detalle |
|-------|---------|
| **Nombre** | Pre-Post rehabilitation fMRI data of post-stroke patients |
| **DOI** | [10.18112/openneuro.ds003999.v1.0.2](https://doi.org/10.18112/openneuro.ds003999.v1.0.2) |
| **Formato** | BIDS 1.2.1 |
| **Licencia** | CC0 |
| **Sujetos originales** | 29 pacientes con ACV hemisférico izquierdo |
| **Sujetos procesados** | 23 (6 excluidos por falta de datos o problemas de calidad) |
| **Sesiones** | `ses-pre` (antes de rehabilitación) y `ses-post` (después) |
| **Tarea** | Reposo (resting-state) |
| **TR** | 3.0 s |

### Autores del dataset original
- Daminov V. (MD, PhD), Novak E. (MD, MSc), Slepnyova N. (MD), Mikhailov D. (MSc), Karpulevich E. (MSc)
- National Medical and Surgical Centre n.a. N.I. Pirogov, Moscow, Russia

---

## Estructura del Proyecto

```
OpenNeuro/
├── datos_originales/        # Dataset BIDS original (29 sujetos)
│   ├── participants.tsv     # Datos demográficos y clínicos
│   ├── dataset_description.json
│   └── sub-XX/              # Datos crudos por sujeto (anat/ + func/)
│
├── preprocesamiento/        # Salidas de fMRIPrep (23 sujetos)
│   ├── sub-XX/              # Datos preprocesados por sujeto
│   │   └── ses-{pre,post}/func/
│   │       ├── *_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz
│   │       ├── *_desc-confounds_timeseries.tsv
│   │       └── *_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz
│   ├── sub-XX.html          # Reportes QC de fMRIPrep
│   └── lesion_check/        # Verificación de lesiones en MNI
│
├── conn/                    # Salidas del pipeline de conectividad motora
│   └── sub-XX/
│       ├── *_desc-smooth_bold.nii.gz         # Imágenes suavizadas
│       ├── *_desc-denoised_bold.nii.gz       # Imágenes denoised
│       └── *_timeseries_motor_AAL.csv        # Series temporales (26 ROIs)
│
├── run_fmriprep.sh          # Script de preprocesamiento (Docker + fMRIPrep)
├── run_conn_all.py          # Pipeline principal: smoothing → denoising → ROIs
├── fix_missing_subjects.py  # Normalización T1w→MNI para sub-15/sub-18 (dipy)
├── check_lesions_mni.py     # Verificación de lesiones en espacio MNI
├── run_nilearn_sub00.py     # Script piloto para sub-00
├── run_conn_sub00.m         # Script MATLAB de referencia
├── requirements.txt         # Dependencias Python
├── license.txt              # Licencia FreeSurfer
└── work/                    # Archivos intermedios de fMRIPrep (temporal)
```

---

## Pipeline de Procesamiento

### Paso 1: Preprocesamiento con fMRIPrep

Se utilizó **fMRIPrep 24.1.1** (vía Docker) para el preprocesamiento estándar de las imágenes fMRI.

**Script:** `run_fmriprep.sh`

**Configuración:**
- Espacio de salida: `MNI152NLin2009cAsym:res-2` + `anat`
- FreeSurfer: deshabilitado (`FS_FLAG=0`)
- CPUs: 8 | Memoria: 16 GB

**Resultado:** Imágenes BOLD preprocesadas en espacio MNI, máscaras cerebrales y matrices de confounds para los 23 sujetos.

**Casos especiales:**
| Sujeto | Problema | Solución |
|--------|----------|----------|
| sub-15, sub-18 | fMRIPrep no normalizó a MNI (solo espacio T1w) debido a lesiones extensas | Normalización manual con **dipy** (registro afín + SyN diffeomórfico) — `fix_missing_subjects.py` |
| sub-30 | fMRIPrep nunca se ejecutó | Se ejecutó fMRIPrep individualmente vía Docker |
| sub-35 | ses-pre tiene solo 30 volúmenes (vs 163 en ses-post) | Filtro bandpass omitido para series cortas (<34 volúmenes) |

### Paso 2: Smoothing Espacial

- **Método:** Gaussian smoothing (nilearn `image.smooth_img`)
- **FWHM:** 6 mm
- **Salida:** `*_desc-smooth_bold.nii.gz`

### Paso 3: Denoising (Limpieza de señal)

- **Método:** `nilearn.image.clean_img`
- **Regresores de confounds** (26 total):
  - 6 parámetros de movimiento rígido
  - 6 derivadas temporales del movimiento
  - 6 parámetros de movimiento al cuadrado
  - 6 derivadas al cuadrado
  - CSF (señal de líquido cefalorraquídeo)
  - Materia blanca (WM)
- **Filtro bandpass:** 0.008 – 0.09 Hz
- **Estandarización:** z-score por muestra
- **Salida:** `*_desc-denoised_bold.nii.gz`

### Paso 4: Extracción de Series Temporales — Corteza Motora

- **Atlas:** AAL (SPM12) — 117 ROIs totales
- **ROIs seleccionadas:** 26 regiones de la red motora
- **Método:** `nilearn.maskers.NiftiLabelsMasker`
- **Salida:** `*_timeseries_motor_AAL.csv` (26 columnas × N volúmenes)

#### ROIs de la Red Motora (26)

| Región | Hemisferio |
|--------|-----------|
| Precentral (M1 — corteza motora primaria) | L, R |
| Supp_Motor_Area (SMA — área motora suplementaria) | L, R |
| Postcentral (S1 — corteza somatosensorial primaria) | L, R |
| Paracentral_Lobule (lobulillo paracentral) | L, R |
| Cerebelum_Crus1 | L, R |
| Cerebelum_Crus2 | L, R |
| Cerebelum_3 | L, R |
| Cerebelum_4_5 | L, R |
| Cerebelum_6 | L, R |
| Cerebelum_7b | L, R |
| Cerebelum_8 | L, R |
| Cerebelum_9 | L, R |
| Cerebelum_10 | L, R |

---

## Sujetos Procesados (23)

```
sub-00  sub-01  sub-11  sub-12  sub-13  sub-15  sub-16  sub-17  sub-18
sub-20  sub-21  sub-22  sub-23  sub-24  sub-25  sub-26  sub-27  sub-28
sub-29  sub-30  sub-33  sub-34  sub-35
```

**Sujetos excluidos** (6): sub-02, sub-03, sub-05, sub-07, sub-10, sub-14 — no cumplieron criterios de calidad o datos incompletos.

---

## Pasos Pendientes

Estos análisis se realizarán en fases posteriores:
1. **Matriz de correlación** entre ROIs motoras
2. **Análisis de grafos** de la red motora
3. **ICA** (Análisis de Componentes Independientes)

---

## Instalación y Uso

### Requisitos
- Python 3.10+
- Docker Desktop (para fMRIPrep)
- ~50 GB de espacio en disco para datos y archivos intermedios

### Instalación de dependencias

```bash
pip install -r requirements.txt
```

### Ejecución

```bash
# 1. Preprocesamiento con fMRIPrep (requiere Docker)
chmod +x run_fmriprep.sh
./run_fmriprep.sh

# 2. Corrección de sujetos con normalización fallida (si aplica)
python fix_missing_subjects.py

# 3. Pipeline principal: Smoothing → Denoising → Series Temporales
python run_conn_all.py
```

---

## Herramientas y Versiones

| Herramienta | Versión | Uso |
|-------------|---------|-----|
| fMRIPrep | 24.1.1 | Preprocesamiento estándar de fMRI |
| Docker | 28.4.0 | Contenedor para fMRIPrep |
| nilearn | 0.13.1 | Smoothing, denoising, extracción de ROIs |
| nibabel | 5.4.2 | Lectura/escritura de imágenes NIfTI |
| dipy | 1.11.0 | Registro T1w→MNI (diffeomórfico) |
| numpy | 2.2.6 | Computación numérica |
| pandas | 2.3.3 | Manejo de tablas y CSVs |
| scipy | 1.15.3 | Filtros y procesamiento de señal |
| scikit-learn | 1.7.2 | Dependencia de nilearn |
| matplotlib | 3.10.8 | Visualización |
| Python | 3.10.11 | Lenguaje principal |

---

## Licencia

El dataset original está bajo licencia **CC0**. El código de este proyecto es de uso académico.
