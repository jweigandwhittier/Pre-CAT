# <img src="https://github.com/jweigandwhittier/Pre-CAT/blob/main/custom/icons/ksp.png" width="50"> Pre-CAT

## Welcome to Pre-CAT 

**Pre-CAT** is a preclinical CEST-MRI data analysis toolbox and Streamlit webapp. **Pre-CAT** was originally designed for processing cardiac and abdominal CEST acquisitions using the radial FLASH sequence described by Weigand-Whittier et al., but has been expanded for use with all ParaVision 6/7 CEST acquisitions.

> ⚠ **Note:**  
> **Pre-CAT** scripts rely on ParaVision method files with specific variable names. **Pre-CAT** is guaranteed to work with the cestsegCSUTE sequence, and should work with any CEST sequence based on the PV 6/7 MT module. **Pre-CAT** will *not* work with PV 360 acquisitions using the new CEST module. This may change in the future.

**Pre-CAT** processes and displays Z-spectra, Lorentzian difference plots, pixelwise maps, and field maps. Processed data is also saved in organized pickle files for downstream tasks.

## Requirements

A pre-prepared Conda environment is available in the `environment.yml` file. To install the environment, run:

```sh
conda env create -f environment.yml
conda activate pre-cat
```

If the process gets stuck, please try switching the conda solver to libmamba:

```sh
conda config --set solver libmamba
conda env create -f environment.yml
conda activate pre-cat
```

Finally, [`BART`](https://mrirecon.github.io/bart/) is also required. Please download the most recent version and follow the instructions in the **README** file for installation.

> ⚠ **Note for Mac Users:**  
> If you're using an **M1 Mac**, please follow the **MacPorts** version of the installation instructions for [`BART`](https://mrirecon.github.io/bart/).

## Instructions

After activating the included Conda environment, navigate to the **Pre-CAT** directory and run:

```sh
streamlit run app.py
```

In-depth instructions are included in the Streamlit interface.

For users unfamiliar with murine and cardiac anatomy, instructions for cardiac ROI prescriptions are included [here](https://github.com/jweigandwhittier/Pre-CAT/blob/main/instructions/cardiac_rois.pdf).

### Demo Video 

[![Watch the video](https://img.youtube.com/vi/BS9N6gIc8yo/hqdefault.jpg)](https://www.youtube.com/embed/BS9N6gIc8yo)

## Example Data

To test **Pre-CAT** with example data, you can download the provided dataset [here](https://doi.org/10.6084/m9.figshare.26112346).

## Troubleshooting 

Please use the [Issues](https://github.com/jweigandwhittier/Pre-CAT/issues) section to report bugs or ask questions.

You are also welcome to contact me directly with any issues or questions at: *jweigandwhittier[at]berkeley[dot]edu*. 

Please add [**Pre-CAT**] to the subject line of your email.

## Citation

**Please cite the associated publications when using Pre-CAT:**

Weigand-Whittier J., Wendland M., Lam B., et al. *Ungated, plug‐and‐play preclinical cardiac CEST‐MRI using radial FLASH with segmented saturation.* Magn Reson Med (2025). https://doi.org/10.1002/mrm.30382

**If you are using CEST-MRF analysis features, please also cite:**

Vladimirov N., Cohen O., Heo H.Y., et al. *Quantitative molecular imaging using deep magnetic resonance fingerprinting.* Nat Protoc (2025). https://doi.org/10.1038/s41596-025-01152-w
