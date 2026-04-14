"""
=============================================================================
 Fix Missing MNI Normalization for sub-15 and sub-18
 
 These subjects only have T1w-space outputs from fMRIPrep (MNI normalization
 failed, likely due to large stroke lesions). This script:
   1. Registers each subject's T1w anatomical → MNI152 2mm template (dipy)
   2. Applies the transform to the T1w-space BOLD and brain mask
   3. Saves outputs with fMRIPrep-compatible filenames so run_conn_all.py works
=============================================================================
"""

import os
import time
import numpy as np
import nibabel as nib
from nilearn import datasets, image
from dipy.align.imaffine import (
    MutualInformationMetric,
    AffineRegistration,
)
from dipy.align.transforms import (
    TranslationTransform3D,
    RigidTransform3D,
    AffineTransform3D,
)
from dipy.align.imwarp import SymmetricDiffeomorphicRegistration
from dipy.align.metrics import CCMetric
import warnings
warnings.filterwarnings('ignore')

# ========================= CONFIGURATION ==================================

DERIVATIVES = r'C:\Users\ASUS\Documents\OpenNeuro\preprocesamiento'
SUBJECTS    = ['sub-15', 'sub-18']
SESSIONS    = ['ses-pre', 'ses-post']

# ========================= LOAD MNI TEMPLATE ===============================

print("Loading MNI152 template (2mm)...")
mni_img  = datasets.load_mni152_template(resolution=2)
mni_data = mni_img.get_fdata().astype(np.float64)
mni_aff  = mni_img.affine

# Also load MNI brain mask for reference
mni_mask_img = datasets.load_mni152_brain_mask(resolution=2)

print(f"  MNI template shape: {mni_data.shape}")
print()

# ========================= HELPER FUNCTIONS ================================

def compute_registration(t1w_img):
    """Compute affine + SyN transform from T1w native → MNI space using dipy."""
    
    t1w_data = t1w_img.get_fdata().astype(np.float64)
    t1w_aff  = t1w_img.affine

    # --- Step 1: Affine registration (translation → rigid → affine) ---
    print("    Computing affine registration (T1w → MNI)...")
    
    nbins     = 64
    level_iters = [1000, 500, 250]
    sigmas    = [3.0, 1.0, 0.0]
    factors   = [4, 2, 1]
    metric    = MutualInformationMetric(nbins, sampling_proportion=0.3)

    affreg = AffineRegistration(
        metric=metric,
        level_iters=level_iters,
        sigmas=sigmas,
        factors=factors,
        verbosity=0,
    )

    # Progressive refinement: translation → rigid → affine
    transform = TranslationTransform3D()
    params0 = None
    translation = affreg.optimize(
        mni_data, t1w_data, transform, params0,
        mni_aff, t1w_aff,
    )

    transform = RigidTransform3D()
    rigid = affreg.optimize(
        mni_data, t1w_data, transform, params0,
        mni_aff, t1w_aff,
        starting_affine=translation.affine,
    )

    transform = AffineTransform3D()
    affine_result = affreg.optimize(
        mni_data, t1w_data, transform, params0,
        mni_aff, t1w_aff,
        starting_affine=rigid.affine,
    )

    print(f"    Affine registration done.")

    # --- Step 2: SyN diffeomorphic registration for nonlinear correction ---
    print("    Computing SyN diffeomorphic registration...")
    
    # First, apply the affine to get an approximate alignment
    t1w_affine_aligned = affine_result.transform(t1w_data)

    syn_metric = CCMetric(3, sigma_diff=2.0)
    syn = SymmetricDiffeomorphicRegistration(
        metric=syn_metric,
        level_iters=[100, 50, 25],
        step_length=0.25,
    )
    syn_result = syn.optimize(mni_data, t1w_affine_aligned)
    
    print(f"    SyN registration done.")

    return affine_result, syn_result


def apply_transform_3d(volume_3d, affine_result, syn_result):
    """Apply affine + SyN to a single 3D volume."""
    aligned = affine_result.transform(volume_3d.astype(np.float64))
    warped  = syn_result.transform(aligned)
    return warped


def normalize_bold(bold_img, affine_result, syn_result):
    """Apply transforms to each volume of a 4D BOLD image."""
    bold_data = bold_img.get_fdata().astype(np.float64)
    n_vols = bold_data.shape[3]
    out_shape = mni_data.shape + (n_vols,)
    out_data  = np.zeros(out_shape, dtype=np.float32)

    for v in range(n_vols):
        if (v + 1) % 20 == 0 or v == 0 or v == n_vols - 1:
            print(f"      Volume {v+1}/{n_vols}", flush=True)
        out_data[..., v] = apply_transform_3d(bold_data[..., v],
                                               affine_result, syn_result)

    return nib.Nifti1Image(out_data, mni_aff)


def normalize_mask(mask_img, affine_result, syn_result):
    """Apply transforms to brain mask and binarize."""
    mask_data = mask_img.get_fdata().astype(np.float64)
    warped = apply_transform_3d(mask_data, affine_result, syn_result)
    # Binarize with threshold 0.5
    warped_bin = (warped > 0.5).astype(np.uint8)
    return nib.Nifti1Image(warped_bin, mni_aff)


# ========================= MAIN ============================================

if __name__ == '__main__':
    total_start = time.time()

    for subj in SUBJECTS:
        print("=" * 60)
        print(f"  {subj}: Normalizing T1w → MNI")
        print("=" * 60)

        t0 = time.time()

        # Load T1w anatomical for registration
        t1w_path = os.path.join(DERIVATIVES, subj, 'anat',
                                f'{subj}_desc-preproc_T1w.nii.gz')
        print(f"  Loading T1w: {t1w_path}")
        t1w_img = nib.load(t1w_path)

        # Compute registration transforms (once per subject)
        affine_result, syn_result = compute_registration(t1w_img)

        # Apply to each session's BOLD and mask
        for ses in SESSIONS:
            print(f"\n  --- {ses} ---")
            func_dir = os.path.join(DERIVATIVES, subj, ses, 'func')

            # Load T1w-space BOLD
            bold_t1w_path = os.path.join(func_dir,
                f'{subj}_{ses}_task-rest_space-T1w_desc-preproc_bold.nii.gz')
            print(f"    Loading BOLD: {bold_t1w_path}")
            bold_img = nib.load(bold_t1w_path)

            # Normalize BOLD → MNI
            print(f"    Normalizing {bold_img.shape[3]} volumes to MNI...")
            bold_mni = normalize_bold(bold_img, affine_result, syn_result)
            
            bold_out = os.path.join(func_dir,
                f'{subj}_{ses}_task-rest_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz')
            bold_mni.to_filename(bold_out)
            print(f"    Saved: {bold_out}")
            del bold_img, bold_mni

            # Load and normalize brain mask
            mask_t1w_path = os.path.join(func_dir,
                f'{subj}_{ses}_task-rest_space-T1w_desc-brain_mask.nii.gz')
            print(f"    Normalizing mask...")
            mask_img = nib.load(mask_t1w_path)
            mask_mni = normalize_mask(mask_img, affine_result, syn_result)
            
            mask_out = os.path.join(func_dir,
                f'{subj}_{ses}_task-rest_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz')
            mask_mni.to_filename(mask_out)
            print(f"    Saved: {mask_out}")
            del mask_img, mask_mni

        elapsed = time.time() - t0
        print(f"\n  {subj} done in {elapsed/60:.1f} min\n")

    total = time.time() - total_start
    print(f"Total elapsed: {total/60:.1f} min")
    print("Done! Now run run_conn_all.py to process these subjects.")
