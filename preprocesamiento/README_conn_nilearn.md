# Análisis de Conectividad Funcional con Nilearn — Post-fMRIPrep

## Descripción General

Este documento describe el pipeline de análisis de conectividad funcional implementado en **Python con Nilearn**, como alternativa al CONN Toolbox de MATLAB. Se aplica sobre los datos ya preprocesados con fMRIPrep v24.1.1, para los 22 sujetos del estudio **"Pre-Post rehabilitation fMRI data of post-stroke patients"** (DOI: 10.18112/openneuro.ds003999.v1.0.2).

El objetivo es comparar la conectividad funcional en reposo entre las sesiones **pre** y **post** rehabilitación en pacientes con lesión en el hemisferio izquierdo.

---

## 1. Requisitos

### 1.1 Software

| Componente | Versión |
|---|---|
| Python | 3.10.11 |
| Nilearn | ≥0.10 |
| Nibabel | ≥5.0 |
| NumPy | 1.26.x |
| Pandas | 2.1.x |
| Scikit-learn | ≥1.3 |
| Matplotlib | 3.10.x |

### 1.2 Instalación

```bash
pip install nilearn nibabel scikit-learn
```

NumPy, Pandas y Matplotlib ya están instalados previamente en el entorno.

### 1.3 Datos de Entrada

Los datos de entrada son los resultados del preprocesamiento con fMRIPrep:

```
derivatives/
└── sub-XX/
    ├── ses-pre/func/
    │   ├── sub-XX_ses-pre_task-rest_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz
    │   ├── sub-XX_ses-pre_task-rest_desc-confounds_timeseries.tsv
    │   └── sub-XX_ses-pre_task-rest_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz
    └── ses-post/func/
        └── ... (misma estructura)
```

---

## 2. Pipeline de Procesamiento

El análisis se ejecuta en 5 pasos secuenciales para cada sujeto y sesión:

### 2.1 Paso 1 — Suavizado Espacial (Spatial Smoothing)

- **Kernel:** Gaussiano, FWHM = 6 mm
- **Propósito:** Mejorar la relación señal-ruido (SNR) y reducir variabilidad anatómica inter-sujeto
- **Función:** `nilearn.image.smooth_img()`
- **Salida:** `sub-XX_ses-YY_task-rest_desc-smooth_bold.nii.gz`

El suavizado de 6 mm es el estándar en análisis de conectividad funcional en reposo, equivalente al valor por defecto del CONN Toolbox.

### 2.2 Paso 2 — Denoising (Regresión de Confounds + Filtrado)

Se eliminan fuentes de ruido no neuronal mediante regresión lineal de confounds y filtrado temporal.

**Confounds regresados (26 regresores):**

| Categoría | Variables | Cantidad |
|---|---|---|
| Movimiento (6 parámetros) | trans_x/y/z, rot_x/y/z | 6 |
| Derivadas del movimiento | trans_x/y/z_derivative1, rot_x/y/z_derivative1 | 6 |
| Cuadrados del movimiento | trans_x/y/z_power2, rot_x/y/z_power2 | 6 |
| Cuadrados de derivadas | trans_x/y/z_derivative1_power2, rot_x/y/z_derivative1_power2 | 6 |
| Señal fisiológica | csf, white_matter | 2 |
| **Total** | | **26** |

Esta estrategia corresponde al modelo de **24 parámetros de movimiento** (Friston et al., 1996) más señales de WM y CSF, comparable a la configuración por defecto de CONN.

**Filtrado temporal (band-pass):**

- Frecuencia de paso alto: **0.008 Hz** (elimina drifts lentos)
- Frecuencia de paso bajo: **0.09 Hz** (retiene fluctuaciones de baja frecuencia de origen neuronal)

**Estandarización:** z-score por muestra (`zscore_sample`)

- **Función:** `nilearn.image.clean_img()`
- **Salida:** `sub-XX_ses-YY_task-rest_desc-denoised_bold.nii.gz`

### 2.3 Paso 3 — Extracción de Series Temporales (ROI-to-ROI)

Se extraen las series temporales promedio de cada región de interés usando el **atlas AAL (Automated Anatomical Labeling)** versión SPM12:

- **Atlas:** AAL-SPM12 (116 regiones cerebrales)
- **Método:** Promedio de todos los vóxeles dentro de cada región
- **Función:** `nilearn.maskers.NiftiLabelsMasker()`
- **Salida:** `sub-XX_ses-YY_task-rest_timeseries_AAL.csv` (matriz de timepoints × 116 regiones)

El atlas AAL parcela el cerebro en 116 regiones anatómicas bilaterales (45 por hemisferio + 26 cerebelares), incluyendo:

- Regiones frontales: frontal superior, medio, inferior, orbital
- Regiones temporales: temporal superior, medio, inferior
- Regiones parietales: parietal superior, inferior, precuneus
- Regiones occipitales: calcarina, cuneus, lingual
- Regiones subcorticales: caudado, putamen, pálido, tálamo, amígdala, hipocampo
- Cerebelo: lóbulos I-X

### 2.4 Paso 4 — Matrices de Conectividad Funcional

Se calcula la correlación de Pearson entre las series temporales de todos los pares de regiones:

- **Métrica:** Correlación de Pearson (ROI-to-ROI)
- **Resultado:** Matriz simétrica de 116 × 116
- **Función:** `nilearn.connectome.ConnectivityMeasure(kind='correlation')`
- **Salida:** `sub-XX_ses-YY_task-rest_connectivity_AAL.csv`

Cada celda (i, j) de la matriz representa la fuerza de la conectividad funcional entre la región i y la región j.

### 2.5 Paso 5 — Visualización

Se generan las siguientes figuras para cada sujeto:

| Figura | Descripción |
|---|---|
| `sub-XX_connectivity_matrices.png` | Matrices de conectividad pre y post lado a lado |
| `sub-XX_connectivity_difference.png` | Matriz de diferencia (post − pre), muestra cambios por rehabilitación |
| `sub-XX_ses-pre_connectome.png` | Connectoma 3D pre-rehabilitación (top 5% conexiones) |
| `sub-XX_ses-post_connectome.png` | Connectoma 3D post-rehabilitación (top 5% conexiones) |

Las figuras de connectoma muestran las conexiones más fuertes proyectadas sobre un cerebro de cristal, con los nodos posicionados en las coordenadas del atlas AAL.

---

## 3. Equivalencia con CONN Toolbox

| Función CONN Toolbox | Equivalente Nilearn |
|---|---|
| Setup → Structural/Functional | Datos ya preprocesados con fMRIPrep |
| Setup → ROIs (atlas) | `nilearn.datasets.fetch_atlas_aal()` |
| Denoising → Confound regression | `nilearn.image.clean_img()` con 26 regresores |
| Denoising → Band-pass filter | Parámetros `high_pass=0.008`, `low_pass=0.09` |
| Denoising → WM/CSF regression | Columnas `csf` y `white_matter` del TSV de fMRIPrep |
| Analysis → ROI-to-ROI | `nilearn.connectome.ConnectivityMeasure(kind='correlation')` |
| Results → Connectivity matrices | `matplotlib` + `nilearn.plotting.plot_connectome()` |
| Results → Second-level (grupo) | Comparación pre vs post con matrices de diferencia |

---

## 4. Sujetos Procesados

Se procesan los 22 sujetos que cumplen el criterio de inclusión (lesión en hemisferio izquierdo):

```
sub-00, sub-01, sub-11, sub-12, sub-13, sub-15, sub-16, sub-17, sub-18,
sub-20, sub-21, sub-22, sub-23, sub-24, sub-25, sub-26, sub-27, sub-28,
sub-29, sub-33, sub-34, sub-35
```

Cada sujeto tiene 2 sesiones: **ses-pre** (antes de rehabilitación) y **ses-post** (después de rehabilitación).

---

## 5. Estructura de Resultados

```
nilearn_results/
├── sub-00/
│   ├── sub-00_ses-pre_task-rest_desc-smooth_bold.nii.gz
│   ├── sub-00_ses-post_task-rest_desc-smooth_bold.nii.gz
│   ├── sub-00_ses-pre_task-rest_desc-denoised_bold.nii.gz
│   ├── sub-00_ses-post_task-rest_desc-denoised_bold.nii.gz
│   ├── sub-00_ses-pre_task-rest_timeseries_AAL.csv
│   ├── sub-00_ses-post_task-rest_timeseries_AAL.csv
│   ├── sub-00_ses-pre_task-rest_connectivity_AAL.csv
│   ├── sub-00_ses-post_task-rest_connectivity_AAL.csv
│   ├── sub-00_connectivity_matrices.png
│   ├── sub-00_connectivity_difference.png
│   ├── sub-00_ses-pre_connectome.png
│   └── sub-00_ses-post_connectome.png
├── sub-01/
│   └── ...
└── sub-35/
    └── ...
```

---

## 6. Librerías Utilizadas

### 6.1 Nilearn

Librería principal de neuroimagen en Python. Proporciona:

- **Manipulación de imágenes:** suavizado, remuestreo, limpieza de señal
- **Extracción de señales:** maskers para atlas, semillas, esferas
- **Análisis de conectividad:** correlación, correlación parcial, tangent
- **Visualización:** connectomas, mapas estadísticos, carpet plots
- **Atlas predefinidos:** AAL, Harvard-Oxford, Schaefer, Destrieux, etc.

### 6.2 Nibabel

Lectura y escritura de formatos de neuroimagen (NIfTI, GIFTI, CIFTI, MGH). Permite cargar y guardar archivos `.nii.gz`.

### 6.3 Scikit-learn

Utilizada internamente por Nilearn para:

- Cálculo de matrices de conectividad (correlación, covarianza)
- Reducción de dimensionalidad (PCA para CompCor)
- Normalización y estandarización de datos

### 6.4 NumPy / Pandas / Matplotlib

- **NumPy:** Operaciones matriciales y estadísticas sobre las matrices de conectividad
- **Pandas:** Lectura de archivos TSV de confounds y exportación de series temporales
- **Matplotlib:** Generación de figuras (matrices de correlación, gráficos de diferencia)

---

## 7. Parámetros Clave

| Parámetro | Valor | Justificación |
|---|---|---|
| FWHM (suavizado) | 6 mm | Estándar para resting-state fMRI, equivalente a CONN |
| High-pass | 0.008 Hz | Elimina drifts lentos (<125 s) |
| Low-pass | 0.09 Hz | Retiene fluctuaciones neuronales (11-125 s) |
| TR | 3.0 s | Tiempo de repetición del dataset |
| Atlas | AAL-SPM12 | 116 ROIs, ampliamente usado en estudios de conectividad |
| Conectividad | Correlación de Pearson | Métrica estándar ROI-to-ROI |
| Umbral connectoma | 95% | Muestra solo el 5% de conexiones más fuertes |
| Estandarización | zscore_sample | Normalización correcta por muestra |

---

## 8. Ejecución

```bash
python run_nilearn_sub00.py
```

El script procesa automáticamente ambas sesiones (pre y post) y genera todos los archivos y visualizaciones listados en la sección 5.

---

## 9. Reproducibilidad

Para reproducir este análisis:

1. Completar el preprocesamiento con fMRIPrep (ver `README_fmriprep.md`)
2. Instalar dependencias: `pip install nilearn nibabel scikit-learn`
3. Ejecutar el script de procesamiento para cada sujeto
4. Los resultados se guardan en `nilearn_results/`

El atlas AAL se descarga automáticamente de los servidores de Nilearn la primera vez y se almacena en caché local.

---

*Documento generado el 7 de abril de 2026.*
