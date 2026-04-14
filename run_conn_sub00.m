%% ==========================================================================
%  CONN Toolbox - Post-fMRIPrep Processing for sub-00
%  Dataset: Pre-Post rehabilitation fMRI data of post-stroke patients
%  Steps: Import fMRIPrep outputs → Spatial Smoothing → Denoising
% ==========================================================================

clear; clc;

%% ---- CONFIGURATION ----
% Update these paths to match your system
bids_dir      = 'C:\Users\ASUS\Documents\OpenNeuro\datos_originales';
derivatives   = 'C:\Users\ASUS\Documents\OpenNeuro\preprocesamiento';
conn_dir      = 'C:\Users\ASUS\Documents\OpenNeuro\conn';
subject_id    = 'sub-00';

% Smoothing kernel (FWHM in mm) - standard for fMRI connectivity
fwhm = 6;

% Repetition Time (from dataset JSON)
TR = 3;

% Band-pass filter for resting-state (Hz)
bp_filter = [0.008, 0.09];

%% ---- LOCATE FILES ----
% Functional files (preprocessed BOLD in MNI space)
func_pre  = fullfile(derivatives, subject_id, 'ses-pre', 'func', ...
    [subject_id '_ses-pre_task-rest_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz']);
func_post = fullfile(derivatives, subject_id, 'ses-post', 'func', ...
    [subject_id '_ses-post_task-rest_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz']);

% Anatomical file (T1w in MNI space)
anat_file = fullfile(derivatives, subject_id, 'anat', ...
    [subject_id '_space-MNI152NLin2009cAsym_res-2_desc-preproc_T1w.nii.gz']);

% Brain mask
mask_file = fullfile(derivatives, subject_id, 'anat', ...
    [subject_id '_space-MNI152NLin2009cAsym_res-2_desc-brain_mask.nii.gz']);

% Tissue segmentation maps (from fMRIPrep)
gm_file  = fullfile(derivatives, subject_id, 'anat', ...
    [subject_id '_space-MNI152NLin2009cAsym_res-2_label-GM_probseg.nii.gz']);
wm_file  = fullfile(derivatives, subject_id, 'anat', ...
    [subject_id '_space-MNI152NLin2009cAsym_res-2_label-WM_probseg.nii.gz']);
csf_file = fullfile(derivatives, subject_id, 'anat', ...
    [subject_id '_space-MNI152NLin2009cAsym_res-2_label-CSF_probseg.nii.gz']);

% Confounds files (from fMRIPrep)
confounds_pre  = fullfile(derivatives, subject_id, 'ses-pre', 'func', ...
    [subject_id '_ses-pre_task-rest_desc-confounds_timeseries.tsv']);
confounds_post = fullfile(derivatives, subject_id, 'ses-post', 'func', ...
    [subject_id '_ses-post_task-rest_desc-confounds_timeseries.tsv']);

% Verify all files exist
files_to_check = {func_pre, func_post, anat_file, gm_file, wm_file, csf_file, confounds_pre, confounds_post};
for i = 1:length(files_to_check)
    if ~isfile(files_to_check{i})
        error('File not found: %s', files_to_check{i});
    end
end
fprintf('All files verified.\n');

%% ---- SETUP CONN BATCH ----
% Create output directory
if ~isfolder(conn_dir)
    mkdir(conn_dir);
end

batch = [];

% --- Basic setup ---
batch.filename = fullfile(conn_dir, [subject_id '_conn_project.mat']);

batch.Setup.isnew     = 1;
batch.Setup.nsubjects  = 1;
batch.Setup.RT         = TR;

% --- Functional data (2 sessions: pre and post) ---
batch.Setup.functionals{1}{1} = func_pre;
batch.Setup.functionals{1}{2} = func_post;

% --- Structural data ---
batch.Setup.structurals{1} = anat_file;

% --- ROIs: tissue masks from fMRIPrep ---
% Grey matter
batch.Setup.rois.names{1}    = 'Grey Matter';
batch.Setup.rois.files{1}{1} = gm_file;
batch.Setup.rois.dimensions{1} = 1;

% White matter
batch.Setup.rois.names{2}    = 'White Matter';
batch.Setup.rois.files{2}{1} = wm_file;
batch.Setup.rois.dimensions{2} = 16;  % CompCor components

% CSF
batch.Setup.rois.names{3}    = 'CSF';
batch.Setup.rois.files{3}{1} = csf_file;
batch.Setup.rois.dimensions{3} = 16;  % CompCor components

% --- Conditions (resting-state = entire session) ---
batch.Setup.conditions.names{1} = 'rest';
batch.Setup.conditions.onsets{1}{1}{1}    = 0;
batch.Setup.conditions.onsets{1}{1}{2}    = 0;
batch.Setup.conditions.durations{1}{1}{1} = inf;
batch.Setup.conditions.durations{1}{1}{2} = inf;

% --- Import fMRIPrep confounds ---
% Read confound regressors from fMRIPrep TSV files
% Using: 6 motion parameters + their derivatives + framewise displacement
confound_names = {'trans_x','trans_y','trans_z','rot_x','rot_y','rot_z', ...
                  'trans_x_derivative1','trans_y_derivative1','trans_z_derivative1', ...
                  'rot_x_derivative1','rot_y_derivative1','rot_z_derivative1', ...
                  'framewise_displacement'};

for ses = 1:2
    if ses == 1
        conf_file = confounds_pre;
    else
        conf_file = confounds_post;
    end
    
    % Read TSV file
    T = readtable(conf_file, 'FileType', 'text', 'Delimiter', '\t');
    
    for c = 1:length(confound_names)
        cname = confound_names{c};
        if ismember(cname, T.Properties.VariableNames)
            values = T.(cname);
            values(isnan(values)) = 0;  % Replace NaN (first timepoint derivatives)
            
            batch.Setup.covariates.names{c} = cname;
            batch.Setup.covariates.files{c}{1}{ses} = values;
        end
    end
end

% --- Tell CONN data is already in MNI space (skip normalization) ---
batch.Setup.preprocessing.steps = {};
batch.Setup.done = 1;

%% ---- SPATIAL SMOOTHING ----
% Apply Gaussian smoothing kernel
batch.Setup.preprocessing.steps{1} = 'functional_smooth';
batch.Setup.preprocessing.fwhm = fwhm;

fprintf('Spatial smoothing configured: FWHM = %d mm\n', fwhm);

%% ---- DENOISING ----
batch.Denoising.filter       = bp_filter;      % Band-pass filter
batch.Denoising.detrending   = 1;              % Linear detrending
batch.Denoising.despiking    = 1;              % Remove intensity spikes
batch.Denoising.regbp        = 1;              % Simultaneous regression + filtering
batch.Denoising.done         = 1;

fprintf('Denoising configured:\n');
fprintf('  Band-pass filter: [%.3f - %.3f] Hz\n', bp_filter(1), bp_filter(2));
fprintf('  Confound regression: %d motion parameters + derivatives\n', length(confound_names));
fprintf('  aCompCor: WM (16 components) + CSF (16 components)\n');

%% ---- FIRST-LEVEL ANALYSIS (optional seed-based connectivity) ----
batch.Analysis.type    = 1;   % 1 = seed-to-voxel
batch.Analysis.sources = {'networks.DefaultMode.MPFC', ...    % Medial Prefrontal Cortex
                          'networks.DefaultMode.LP(L)', ...   % Left Lateral Parietal
                          'networks.DefaultMode.LP(R)', ...   % Right Lateral Parietal  
                          'networks.DefaultMode.PCC'};        % Posterior Cingulate Cortex
batch.Analysis.done    = 1;

fprintf('First-level analysis: Seed-to-voxel (Default Mode Network seeds)\n');

%% ---- RUN CONN ----
fprintf('\n============================================\n');
fprintf(' Running CONN Toolbox for %s\n', subject_id);
fprintf('============================================\n\n');

conn_batch(batch);

fprintf('\n============================================\n');
fprintf(' CONN processing complete!\n');
fprintf(' Results saved to: %s\n', conn_dir);
fprintf('============================================\n');
