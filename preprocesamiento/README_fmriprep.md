# Preprocesamiento fMRI con fMRIPrep — Documentación del Flujo de Trabajo

## Descripción General

Este documento describe el proceso completo de preprocesamiento de imágenes de resonancia magnética funcional (fMRI) del dataset **"Pre-Post rehabilitation fMRI data of post-stroke patients"** (DOI: 10.18112/openneuro.ds003999.v1.0.2), utilizando **fMRIPrep v24.1.1** ejecutado a través de **Docker** en un entorno **Windows**.

---

## 1. Requisitos Previos

### 1.1 Docker Desktop para Windows

fMRIPrep es una herramienta desarrollada originalmente para sistemas Linux. Sin embargo, gracias a la tecnología de **contenedores Docker**, es posible ejecutarla en cualquier sistema operativo (Windows, macOS o Linux) sin necesidad de instalar manualmente las decenas de dependencias que requiere.

**¿Qué es Docker?**

Docker es una plataforma de virtualización ligera que empaqueta una aplicación junto con todas sus dependencias (librerías, herramientas, configuraciones) dentro de un "contenedor" aislado. A diferencia de una máquina virtual completa, un contenedor Docker comparte el kernel del sistema operativo anfitrión, lo que lo hace mucho más eficiente en recursos.

**¿Por qué Docker permite ejecutar fMRIPrep en Windows?**

La imagen Docker de fMRIPrep contiene un sistema Linux completo con todas las herramientas de neuroimagen preinstaladas:

- **fMRIPrep** (pipeline principal)
- **FreeSurfer** (segmentación y reconstrucción cortical)
- **ANTs** (registro y normalización)
- **FSL** (herramientas de análisis)
- **Nipype** (motor de flujos de trabajo)
- **Python** y todas las librerías necesarias

Cuando se ejecuta `docker run`, Docker crea un contenedor Linux aislado dentro de Windows, monta las carpetas del sistema anfitrión como volúmenes, ejecuta fMRIPrep y devuelve los resultados directamente a las carpetas de Windows. El usuario no necesita interactuar con Linux en ningún momento.

**Instalación:**

1. Descargar Docker Desktop desde: https://www.docker.com/products/docker-desktop
2. Instalar y reiniciar el equipo
3. Verificar que Docker esté funcionando (ícono en la barra de tareas)

**Descarga de la imagen fMRIPrep:**

```bash
docker pull nipreps/fmriprep:24.1.1
```

Esta descarga (~15-20 GB) solo se realiza una vez. Todas las ejecuciones posteriores utilizan la imagen almacenada localmente.

### 1.2 Licencia de FreeSurfer

FreeSurfer es un software de análisis de neuroimagen desarrollado por el Martinos Center for Biomedical Imaging (Harvard/MIT). Aunque es gratuito para uso académico, requiere un archivo de licencia para funcionar.

**Obtención de la licencia (gratuita):**

1. Registrarse en: https://surfer.nmr.mgh.harvard.edu/registration.html
2. Completar el formulario con nombre, correo electrónico e institución
3. Recibir por correo el archivo `license.txt`
4. Guardar el archivo en la carpeta raíz del dataset

**Importante:** El archivo de licencia es necesario incluso cuando FreeSurfer no se ejecuta completamente (flag `--fs-no-reconall`), ya que fMRIPrep valida su existencia al inicio del procesamiento.

**Ubicación en este proyecto:**

```
C:\Users\ASUS\Documents\OpenNeuro\license.txt
```

---

## 2. Dataset de Entrada

### 2.1 Estructura BIDS

El dataset sigue el estándar BIDS (Brain Imaging Data Structure) v1.2.1:

```
OpenNeuro/
├── dataset_description.json
├── participants.tsv
├── participants.json
├── license.txt                          ← Licencia de FreeSurfer
├── sub-00/
│   ├── ses-pre/
│   │   ├── anat/
│   │   │   ├── sub-00_ses-pre_T1w.nii.gz       ← Imagen anatómica
│   │   │   └── sub-00_ses-pre_T1w.json          ← Metadatos
│   │   └── func/
│   │       ├── sub-00_ses-pre_task-rest_bold.nii.gz  ← fMRI en reposo
│   │       └── sub-00_ses-pre_task-rest_bold.json    ← Metadatos
│   └── ses-post/
│       ├── anat/
│       └── func/
├── sub-01/
│   └── ...
└── sub-35/
    └── ...
```

### 2.2 Parámetros de Adquisición

| Parámetro | Anatómica (T1w) | Funcional (BOLD) |
|---|---|---|
| Secuencia | MPRAGE (3D) | EPI (2D) |
| TR | 2.3 s | 3.0 s |
| TE | 2.26 ms | 30 ms |
| Resolución | 1 mm isotrópico | 3 mm, 41 cortes |
| Matriz | 256 × 256 | 128 × 128 |
| Volúmenes | 1 | 163 |
| Duración | ~5 min | ~8 min 9 s |

---

## 3. Ejecución de fMRIPrep

### 3.1 Comando de Ejecución

Desde PowerShell en Windows:

```powershell
docker run --rm `
    -v C:\Users\ASUS\Documents\OpenNeuro:/data:ro `
    -v C:\Users\ASUS\Documents\OpenNeuro\derivatives:/out `
    -v C:\Users\ASUS\Documents\OpenNeuro\work:/work `
    -v C:\Users\ASUS\Documents\OpenNeuro\license.txt:/opt/freesurfer/license.txt:ro `
    nipreps/fmriprep:24.1.1 `
    /data /out participant `
    --participant-label 00 `
    --output-spaces MNI152NLin2009cAsym:res-2 anat `
    --nprocs 8 `
    --mem-mb 16384 `
    --work-dir /work `
    --skip_bids_validation `
    --fs-no-reconall
```

### 3.2 Explicación de los Parámetros

| Parámetro | Descripción |
|---|---|
| `--rm` | Elimina el contenedor al finalizar (libera espacio) |
| `-v ..:/data:ro` | Monta el dataset BIDS como solo lectura dentro del contenedor |
| `-v ..:/out` | Monta la carpeta de salida para los resultados |
| `-v ..:/work` | Monta la carpeta de trabajo para archivos intermedios |
| `-v license.txt:/opt/freesurfer/license.txt:ro` | Monta la licencia de FreeSurfer |
| `--participant-label 00` | Procesa únicamente el sujeto sub-00 |
| `--output-spaces MNI152NLin2009cAsym:res-2 anat` | Normaliza al espacio MNI (2mm) y al espacio nativo T1w |
| `--nprocs 8` | Utiliza 8 núcleos de CPU |
| `--mem-mb 16384` | Limita el uso de memoria a 16 GB |
| `--work-dir /work` | Directorio para archivos temporales |
| `--skip_bids_validation` | Omite la validación BIDS (ya validado previamente) |
| `--fs-no-reconall` | Desactiva la reconstrucción cortical de FreeSurfer |

### 3.3 Montaje de Volúmenes Docker

El siguiente diagrama ilustra cómo Docker conecta las carpetas de Windows con las rutas internas del contenedor Linux:

```
WINDOWS (Host)                              DOCKER (Contenedor Linux)
─────────────────                           ─────────────────────────
C:\...\OpenNeuro\          ──(ro)──►        /data/
C:\...\OpenNeuro\derivatives\  ──────►      /out/
C:\...\OpenNeuro\work\         ──────►      /work/
C:\...\OpenNeuro\license.txt   ──(ro)──►    /opt/freesurfer/license.txt
```

`ro` = read-only (solo lectura): protege los datos originales de modificaciones accidentales.

---

## 4. Pipeline de Preprocesamiento

fMRIPrep ejecuta automáticamente los siguientes pasos:

### 4.1 Preprocesamiento Anatómico

1. **Corrección de inhomogeneidad de campo (N4):** Corrige variaciones de intensidad causadas por el campo magnético.
2. **Extracción de cerebro (brain extraction):** Elimina el cráneo y tejidos no cerebrales.
3. **Segmentación tisular:** Clasifica cada vóxel en sustancia gris (GM), sustancia blanca (WM) o líquido cefalorraquídeo (CSF).
4. **Normalización espacial:** Registra la imagen T1w al espacio estándar MNI152NLin2009cAsym.

### 4.2 Preprocesamiento Funcional

1. **Generación de imagen de referencia:** Crea un volumen de referencia a partir de la serie temporal BOLD.
2. **Slice Timing Correction:** Corrige las diferencias temporales entre cortes adquiridos de forma intercalada.
3. **Corrección de movimiento (Head Motion Correction):** Alinea todos los volúmenes al volumen de referencia, estimando 6 parámetros de movimiento (3 traslaciones + 3 rotaciones).
4. **Co-registro funcional-anatómico:** Alinea la imagen funcional con la anatómica T1w del mismo sujeto.
5. **Normalización al espacio MNI:** Aplica la transformación calculada en el paso anatómico para llevar los datos funcionales al espacio estándar.
6. **Generación de confounds:** Calcula variables de confusión (movimiento, CompCor, señal global, framewise displacement) para su uso posterior en el denoising.

---

## 5. Archivos de Salida

### 5.1 Estructura de Resultados

```
derivatives/
├── dataset_description.json
├── sub-00.html                               ← Reporte visual de calidad
├── sub-00/
│   ├── anat/
│   │   ├── sub-00_desc-preproc_T1w.nii.gz              ← T1w preprocesado (nativo)
│   │   ├── sub-00_desc-brain_mask.nii.gz                ← Máscara cerebral
│   │   ├── sub-00_dseg.nii.gz                           ← Segmentación tisular
│   │   ├── sub-00_label-GM_probseg.nii.gz               ← Mapa de sustancia gris
│   │   ├── sub-00_label-WM_probseg.nii.gz               ← Mapa de sustancia blanca
│   │   ├── sub-00_label-CSF_probseg.nii.gz              ← Mapa de LCR
│   │   ├── sub-00_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz  ← T1w en MNI
│   │   ├── sub-00_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5       ← Transformación
│   │   └── sub-00_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5       ← Transformación inversa
│   ├── ses-pre/
│   │   └── func/
│   │       ├── sub-00_ses-pre_task-rest_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz  ← BOLD preprocesado (MNI)
│   │       ├── sub-00_ses-pre_task-rest_space-T1w_desc-preproc_bold.nii.gz                        ← BOLD preprocesado (nativo)
│   │       ├── sub-00_ses-pre_task-rest_desc-confounds_timeseries.tsv                             ← Confounds
│   │       └── sub-00_ses-pre_task-rest_desc-brain_mask.nii.gz                                    ← Máscara funcional
│   ├── ses-post/
│   │   └── func/
│   │       └── ... (misma estructura que ses-pre)
│   └── figures/
│       ├── sub-00_dseg.svg                                    ← Segmentación
│       ├── sub-00_space-MNI152NLin2009cAsym_T1w.svg          ← Normalización
│       ├── sub-00_ses-pre_task-rest_desc-coreg_bold.svg       ← Co-registro
│       ├── sub-00_ses-pre_task-rest_desc-carpetplot_bold.svg  ← Carpet plot
│       └── ... (figuras adicionales por sesión)
└── logs/
    └── CITATION.md
```

### 5.2 Reporte de Calidad

fMRIPrep genera un reporte HTML por sujeto (`sub-00.html`) que permite verificar visualmente:

- La segmentación anatómica
- La normalización al espacio MNI
- El co-registro funcional-anatómico
- Los carpet plots (representación de toda la serie temporal)
- Los parámetros de movimiento estimados

---

## 6. Librerías y Herramientas Utilizadas

La imagen Docker de fMRIPrep empaqueta todas las herramientas necesarias para el preprocesamiento. A continuación se detallan las librerías principales y su función dentro del pipeline.

### 6.1 Herramientas de Neuroimagen (C/C++)

| Herramienta | Función en fMRIPrep |
|---|---|
| **ANTs** (Advanced Normalization Tools) | Registro no lineal, normalización al espacio MNI, corrección de inhomogeneidad de campo N4 |
| **FreeSurfer** | Segmentación tisular, reconstrucción de superficies corticales (desactivada en este proyecto con `--fs-no-reconall`) |
| **FSL** (FMRIB Software Library) | Extracción cerebral (BET), corrección de movimiento (MCFLIRT), slice timing correction |
| **AFNI** | Corrección de despiking (eliminación de picos de intensidad anómalos), herramientas auxiliares |
| **Convert3D (C3D)** | Conversión y manipulación de formatos de imagen médica |

### 6.2 Librerías Python del Pipeline

| Librería | Función |
|---|---|
| **Nipype** | Motor de flujos de trabajo — conecta todas las herramientas en un pipeline reproducible y paralelizable |
| **Nilearn** | Procesamiento de señales cerebrales, limpieza de confounds, manipulación de imágenes NIfTI |
| **Nibabel** | Lectura/escritura de archivos NIfTI, GIFTI y CIFTI |
| **NumPy** | Operaciones numéricas y manejo de matrices multidimensionales |
| **SciPy** | Interpolación, filtrado de señales, operaciones estadísticas |
| **Pandas** | Manejo de tablas de confounds (archivos TSV) |
| **Matplotlib** | Generación de figuras y gráficos para los reportes de calidad |
| **Scikit-learn** | Cálculo de componentes CompCor mediante PCA (Análisis de Componentes Principales) |
| **TemplateFlow** | Descarga y gestión de templates cerebrales estandarizados (MNI152, etc.) |
| **SDCFlows** | Corrección de distorsiones espaciales por susceptibilidad magnética |
| **NiWorkflows** | Flujos de trabajo reutilizables para generación de reportes visuales (HTML + SVG) |
| **SMRiPrep** | Sub-pipeline dedicado al preprocesamiento anatómico (T1w/T2w) |

### 6.3 Diagrama de Dependencias

```
fMRIPrep (pipeline principal)
 ├── SMRiPrep ─── Preprocesamiento anatómico
 │    ├── ANTs ──── Normalización, corrección N4
 │    ├── FreeSurfer ── Segmentación (opcional)
 │    └── FSL ──── Brain extraction (BET)
 │
 ├── Nipype ────── Motor de flujos de trabajo
 │
 ├── SDCFlows ─── Corrección de distorsiones
 │
 ├── FSL ──────── Motion correction (MCFLIRT), slice timing
 ├── AFNI ─────── Despiking
 │
 ├── Nilearn ──── Limpieza de señal, confounds
 ├── Nibabel ──── Lectura/escritura de archivos NIfTI
 ├── TemplateFlow ── Templates MNI
 │
 └── NiWorkflows ── Reportes HTML + figuras SVG
```

Todas estas herramientas están preinstaladas en la imagen `nipreps/fmriprep:24.1.1` (~15-20 GB). No es necesario instalar ninguna de ellas manualmente.

---

## 7. Información del Sistema

| Componente | Versión/Detalle |
|---|---|
| Sistema operativo | Windows 10/11 |
| Plataforma de ejecución | Docker Desktop |
| fMRIPrep | v24.1.1 |
| FreeSurfer | Incluido en Docker (licencia requerida) |
| Espacio estándar | MNI152NLin2009cAsym, resolución 2 mm |
| FreeSurfer reconall | Desactivado (`--fs-no-reconall`) |

---

## 8. Reproducibilidad

Para reproducir exactamente este preprocesamiento:

1. Instalar Docker Desktop
2. Descargar la imagen: `docker pull nipreps/fmriprep:24.1.1`
3. Obtener la licencia de FreeSurfer (gratuita)
4. Ejecutar el comando documentado en la sección 3.1 para cada sujeto

La imagen Docker garantiza que todas las versiones de software son idénticas independientemente del sistema operativo utilizado, asegurando la reproducibilidad completa del análisis.

---

*Documento generado el 18 de marzo de 2026.*
