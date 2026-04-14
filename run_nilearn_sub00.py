"""
=============================================================================
 Nilearn Post-fMRIPrep Processing for sub-00
 Dataset: Pre-Post rehabilitation fMRI data of post-stroke patients
 Steps: Spatial Smoothing → Denoising → Connectivity Analysis
=============================================================================

 Requirements:
   pip install nilearn nibabel numpy pandas scikit-learn matplotlib

 Usage:
   python run_nilearn_sub00.py
=============================================================================
"""

import os
import numpy as np
import pandas as pd
import nibabel as nib
from nilearn import image, plotting, datasets, maskers, connectome
from nilearn.interfaces.fmriprep import load_confounds
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ========================= CONFIGURATION ==================================

BIDS_DIR = r'C:\Users\ASUS\Documents\OpenNeuro\datos_originales'
DERIVATIVES = r'C:\Users\ASUS\Documents\OpenNeuro\preprocesamiento'
OUTPUT_DIR = r'C:\Users\ASUS\Documents\OpenNeuro\conn'
SUBJECT = 'sub-00'

# Smoothing kernel (FWHM in mm)
FWHM = 6

# Band-pass filter (Hz) for resting-state
HIGH_PASS = 0.008
LOW_PASS = 0.09

# Repetition Time
TR = 3.0

# ========================= CREATE OUTPUT DIR ===============================

os.makedirs(OUTPUT_DIR, exist_ok=True)
sub_out = os.path.join(OUTPUT_DIR, SUBJECT)
os.makedirs(sub_out, exist_ok=True)

print("=" * 60)
print(f"  Nilearn Processing: {SUBJECT}")
print("=" * 60)

# ========================= LOCATE FILES ====================================

sessions = ['ses-pre', 'ses-post']

func_files = {}
confound_files = {}
mask_files = {}

for ses in sessions:
    func_files[ses] = os.path.join(
        DERIVATIVES, SUBJECT, ses, 'func',
        f'{SUBJECT}_{ses}_task-rest_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz'
    )
    confound_files[ses] = os.path.join(
        DERIVATIVES, SUBJECT, ses, 'func',
        f'{SUBJECT}_{ses}_task-rest_desc-confounds_timeseries.tsv'
    )
    mask_files[ses] = os.path.join(
        DERIVATIVES, SUBJECT, ses, 'func',
        f'{SUBJECT}_{ses}_task-rest_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz'
    )

anat_file = os.path.join(
    DERIVATIVES, SUBJECT, 'anat',
    f'{SUBJECT}_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz'
)

# Verify files exist
for ses in sessions:
    for label, f in [('Functional', func_files[ses]),
                     ('Confounds', confound_files[ses]),
                     ('Mask', mask_files[ses])]:
        if not os.path.isfile(f):
            raise FileNotFoundError(f'{label} ({ses}): {f}')

print("[OK] All files found.\n")

# ========================= STEP 1: SPATIAL SMOOTHING =======================

print(f"STEP 1: Spatial Smoothing (FWHM = {FWHM} mm)")
print("-" * 60)

smoothed = {}
for ses in sessions:
    print(f"  Smoothing {ses}...", end=' ')
    smoothed[ses] = image.smooth_img(func_files[ses], fwhm=FWHM)

    # Save smoothed image
    out_path = os.path.join(sub_out, f'{SUBJECT}_{ses}_task-rest_desc-smooth_bold.nii.gz')
    smoothed[ses].to_filename(out_path)
    print(f"done → {os.path.basename(out_path)}")

print()

# ========================= STEP 2: DENOISING ===============================

print(f"STEP 2: Denoising (confound regression + band-pass filter)")
print(f"  Band-pass: [{HIGH_PASS} - {LOW_PASS}] Hz")
print("-" * 60)

# Confound columns to regress out:
# - 6 motion parameters + derivatives + power2 (24 motion params)
# - Framewise displacement (for scrubbing)
# - CompCor components from WM and CSF
confound_columns = [
    'trans_x', 'trans_y', 'trans_z', 'rot_x', 'rot_y', 'rot_z',
    'trans_x_derivative1', 'trans_y_derivative1', 'trans_z_derivative1',
    'rot_x_derivative1', 'rot_y_derivative1', 'rot_z_derivative1',
    'trans_x_power2', 'trans_y_power2', 'trans_z_power2',
    'rot_x_power2', 'rot_y_power2', 'rot_z_power2',
    'trans_x_derivative1_power2', 'trans_y_derivative1_power2', 'trans_z_derivative1_power2',
    'rot_x_derivative1_power2', 'rot_y_derivative1_power2', 'rot_z_derivative1_power2',
    'csf', 'white_matter'
]

cleaned = {}
for ses in sessions:
    print(f"  Denoising {ses}...", end=' ')

    # Load confounds from fMRIPrep TSV
    conf_df = pd.read_csv(confound_files[ses], sep='\t')

    # Select available columns
    available_cols = [c for c in confound_columns if c in conf_df.columns]
    confounds_matrix = conf_df[available_cols].fillna(0).values

    print(f"({len(available_cols)} regressors) ", end='')

    # Apply cleaning: confound regression + band-pass + standardization
    cleaned[ses] = image.clean_img(
        smoothed[ses],
        confounds=confounds_matrix,
        high_pass=HIGH_PASS,
        low_pass=LOW_PASS,
        t_r=TR,
        standardize='zscore_sample',
        mask_img=mask_files[ses]
    )

    # Save cleaned image
    out_path = os.path.join(sub_out, f'{SUBJECT}_{ses}_task-rest_desc-denoised_bold.nii.gz')
    cleaned[ses].to_filename(out_path)
    print(f"done → {os.path.basename(out_path)}")

print()

# ========================= STEP 3: EXTRACT TIME SERIES =====================

print("STEP 3: Extract time series using AAL atlas (116 ROIs)")
print("-" * 60)

# Fetch AAL atlas (Automated Anatomical Labeling)
atlas = datasets.fetch_atlas_aal(version='SPM12')
atlas_img = atlas.maps
atlas_labels = atlas.labels

# Create masker for extracting ROI time series
roi_masker = maskers.NiftiLabelsMasker(
    labels_img=atlas_img,
    labels=atlas_labels,
    standardize='zscore_sample',
    resampling_target='data',
    memory='nilearn_cache'
)

timeseries = {}
for ses in sessions:
    print(f"  Extracting {ses}...", end=' ')
    timeseries[ses] = roi_masker.fit_transform(cleaned[ses])
    print(f"done → shape: {timeseries[ses].shape} (timepoints × regions)")

    # Save time series as CSV
    ts_df = pd.DataFrame(timeseries[ses], columns=atlas_labels[:timeseries[ses].shape[1]])
    ts_path = os.path.join(sub_out, f'{SUBJECT}_{ses}_task-rest_timeseries_AAL.csv')
    ts_df.to_csv(ts_path, index=False)

print()

# ========================= STEP 4: CONNECTIVITY MATRICES ===================

print("STEP 4: Compute functional connectivity matrices")
print("-" * 60)

conn_measure = connectome.ConnectivityMeasure(kind='correlation')

matrices = {}
for ses in sessions:
    print(f"  Computing {ses}...", end=' ')
    matrices[ses] = conn_measure.fit_transform([timeseries[ses]])[0]

    # Save matrix
    mat_path = os.path.join(sub_out, f'{SUBJECT}_{ses}_task-rest_connectivity_AAL.csv')
    pd.DataFrame(matrices[ses]).to_csv(mat_path, index=False)
    print(f"done → {matrices[ses].shape[0]}×{matrices[ses].shape[1]} matrix")

print()

# ========================= STEP 5: VISUALIZATION ===========================

print("STEP 5: Generating visualizations")
print("-" * 60)

# --- 5a: Connectivity matrices side by side ---
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

for idx, ses in enumerate(sessions):
    np.fill_diagonal(matrices[ses], 0)
    im = axes[idx].imshow(matrices[ses], cmap='RdBu_r', vmin=-0.8, vmax=0.8)
    axes[idx].set_title(f'{SUBJECT} - {ses}', fontsize=14)
    axes[idx].set_xlabel('Brain regions (AAL)')
    axes[idx].set_ylabel('Brain regions (AAL)')

fig.colorbar(im, ax=axes, shrink=0.8, label='Pearson correlation')
fig.suptitle('Functional Connectivity Matrices (Pre vs Post Rehabilitation)', fontsize=16)
plt.tight_layout()

fig_path = os.path.join(sub_out, f'{SUBJECT}_connectivity_matrices.png')
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"  Connectivity matrices → {os.path.basename(fig_path)}")

# --- 5b: Difference matrix (Post - Pre) ---
diff_matrix = matrices['ses-post'] - matrices['ses-pre']

fig, ax = plt.subplots(figsize=(9, 8))
np.fill_diagonal(diff_matrix, 0)
im = ax.imshow(diff_matrix, cmap='RdBu_r', vmin=-0.5, vmax=0.5)
ax.set_title(f'{SUBJECT}: Connectivity Change (Post - Pre)', fontsize=14)
ax.set_xlabel('Brain regions (AAL)')
ax.set_ylabel('Brain regions (AAL)')
fig.colorbar(im, shrink=0.8, label='Δ Pearson correlation')
plt.tight_layout()

fig_path = os.path.join(sub_out, f'{SUBJECT}_connectivity_difference.png')
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"  Difference matrix     → {os.path.basename(fig_path)}")

# --- 5c: Connectome visualization on brain ---
for ses in sessions:
    coords = plotting.find_parcellation_cut_coords(labels_img=atlas_img)
    fig_path = os.path.join(sub_out, f'{SUBJECT}_{ses}_connectome.png')

    plotting.plot_connectome(
        matrices[ses],
        coords,
        edge_threshold='95%',
        title=f'{SUBJECT} {ses} - Top 5% connections',
        output_file=fig_path,
        colorbar=True,
        node_size=20
    )
    print(f"  Connectome ({ses})   → {os.path.basename(fig_path)}")

print()

# ========================= SUMMARY =========================================

print("=" * 60)
print("  PROCESSING COMPLETE")
print("=" * 60)
print(f"  Results saved to: {sub_out}")
print()
print("  Output files:")
for f in sorted(os.listdir(sub_out)):
    size_mb = os.path.getsize(os.path.join(sub_out, f)) / (1024 * 1024)
    print(f"    {f} ({size_mb:.1f} MB)")
print()
print("  Key statistics:")
for ses in sessions:
    mean_conn = np.mean(np.abs(matrices[ses][np.triu_indices_from(matrices[ses], k=1)]))
    print(f"    {ses}: Mean |connectivity| = {mean_conn:.4f}")
print()
mean_diff = np.mean(diff_matrix[np.triu_indices_from(diff_matrix, k=1)])
print(f"    Mean change (post-pre): {mean_diff:.4f}")
print("=" * 60)
