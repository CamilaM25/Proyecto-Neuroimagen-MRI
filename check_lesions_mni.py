"""
Verificación de lesiones en espacio nativo vs MNI normalizado.
Compara T1w preprocesado (nativo) con T1w en espacio MNI para verificar
que las lesiones se preservan tras la normalización.
"""
import os
import numpy as np
import nibabel as nib
from nilearn import plotting, image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DERIVATIVES = r'C:\Users\ASUS\Documents\OpenNeuro\preprocesamiento'
OUTPUT_DIR = r'C:\Users\ASUS\Documents\OpenNeuro\preprocesamiento\lesion_check'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sujetos con anat en preprocesamiento (tienen T1w en MNI)
subjects = ['sub-00', 'sub-01', 'sub-11', 'sub-12', 'sub-13',
            'sub-15', 'sub-16', 'sub-17', 'sub-18',
            'sub-20', 'sub-21', 'sub-22', 'sub-23', 'sub-24',
            'sub-25', 'sub-26', 'sub-27', 'sub-28', 'sub-29',
            'sub-33', 'sub-34', 'sub-35']

print("=" * 70)
print("  VERIFICACIÓN DE LESIONES: Espacio Nativo vs MNI")
print("=" * 70)

for sub in subjects:
    # T1w en espacio nativo (preprocesado)
    native_t1 = os.path.join(DERIVATIVES, sub, 'anat',
                             f'{sub}_desc-preproc_T1w.nii.gz')
    # T1w en espacio MNI
    mni_t1 = os.path.join(DERIVATIVES, sub, 'anat',
                          f'{sub}_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz')
    # Brain mask en MNI
    mni_mask = os.path.join(DERIVATIVES, sub, 'anat',
                            f'{sub}_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz')
    # Segmentation en MNI
    mni_dseg = os.path.join(DERIVATIVES, sub, 'anat',
                            f'{sub}_space-MNI152NLin2009cAsym_res-2_dseg.nii.gz')

    if not os.path.isfile(native_t1):
        print(f"  [{sub}] SKIP - No native T1w found")
        continue
    if not os.path.isfile(mni_t1):
        print(f"  [{sub}] SKIP - No MNI T1w found")
        continue

    print(f"\n  [{sub}] Generating comparison...")

    # --- Figure 1: Native T1w (3 views) ---
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'{sub}: Lesion Verification — Native (top) vs MNI (bottom)', fontsize=16, fontweight='bold')

    # Native T1w - axial slices focusing on lesion area
    native_img = nib.load(native_t1)
    mni_img = nib.load(mni_t1)

    # Top row: Native T1w
    for idx, display_mode in enumerate(['x', 'y', 'z']):
        ax = axes[0, idx]
        display = plotting.plot_anat(native_t1, display_mode=display_mode,
                                     cut_coords=5, axes=ax,
                                     title=f'Native T1w ({display_mode}-cuts)',
                                     annotate=True, draw_cross=False)

    # Bottom row: MNI T1w
    for idx, display_mode in enumerate(['x', 'y', 'z']):
        ax = axes[1, idx]
        display = plotting.plot_anat(mni_t1, display_mode=display_mode,
                                     cut_coords=5, axes=ax,
                                     title=f'MNI T1w ({display_mode}-cuts)',
                                     annotate=True, draw_cross=False)

    plt.tight_layout()
    fig_path = os.path.join(OUTPUT_DIR, f'{sub}_native_vs_mni.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    → {os.path.basename(fig_path)}")

    # --- Figure 2: MNI T1w with segmentation overlay ---
    if os.path.isfile(mni_dseg):
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle(f'{sub}: Segmentation in MNI space (GM/WM/CSF)', fontsize=14, fontweight='bold')

        for idx, display_mode in enumerate(['x', 'y', 'z']):
            ax = axes[idx]
            display = plotting.plot_anat(mni_t1, display_mode=display_mode,
                                         cut_coords=5, axes=ax,
                                         title=f'MNI + Segmentation ({display_mode})',
                                         annotate=True, draw_cross=False)
            display.add_contours(mni_dseg, levels=[0.5, 1.5, 2.5],
                                colors=['b', 'g', 'r'], linewidths=0.5)

        plt.tight_layout()
        fig_path = os.path.join(OUTPUT_DIR, f'{sub}_mni_segmentation.png')
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"    → {os.path.basename(fig_path)}")

    # --- Stats: Check intensity distribution in lesion hemisphere ---
    mni_data = mni_img.get_fdata()
    # Left hemisphere = right side of image (radiological convention in MNI)
    mid_x = mni_data.shape[0] // 2
    left_hemi = mni_data[mid_x:, :, :]  # Left hemisphere (lesion side)
    right_hemi = mni_data[:mid_x, :, :]  # Right hemisphere (healthy)

    left_mean = np.mean(left_hemi[left_hemi > 0])
    right_mean = np.mean(right_hemi[right_hemi > 0])
    left_nonzero = np.count_nonzero(left_hemi)
    right_nonzero = np.count_nonzero(right_hemi)
    asymmetry = (right_nonzero - left_nonzero) / max(right_nonzero, 1) * 100

    print(f"    Left hemi:  mean={left_mean:.1f}, voxels={left_nonzero}")
    print(f"    Right hemi: mean={right_mean:.1f}, voxels={right_nonzero}")
    print(f"    Asymmetry:  {asymmetry:.1f}% fewer voxels in left (lesion) hemisphere")

    if asymmetry > 5:
        print(f"    ⚠ Notable asymmetry detected — lesion likely visible in MNI")
    elif asymmetry > 1:
        print(f"    ✓ Mild asymmetry — lesion may be partially preserved")
    else:
        print(f"    ⚡ Low asymmetry — check visually if lesion is present")

print("\n" + "=" * 70)
print(f"  Images saved to: {OUTPUT_DIR}")
print("  Open the PNG files to visually verify lesion preservation.")
print("  Also check fMRIPrep HTML reports in preprocesamiento/ for QA.")
print("=" * 70)
