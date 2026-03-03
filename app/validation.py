#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 15:47:46 2026

@author: jonah
"""
import os
import importlib.metadata
import scripts.BrukerMRI as bruker

def check_mrf_tools_installed():
    """
    Validates the environment.
    """
    required_packages = ['cest_mrf', 'pypulseq', 'BMCSimulator']
    packages_found = all(importlib.util.find_spec(pkg) is not None for pkg in required_packages)
    if not packages_found:
        return False
    return True

def validate_radial(path):
    """
    Check the existence of required files in a radial experiment.
    """
    required_files = ['method', 'acqp', 'traj', 'fid']
    missing = [file for file in required_files if not os.path.isfile(os.path.join(path, file))]
    return missing

def validate_rectilinear(path):
    """
    Check the existence of required files for rectilinear acquisition.
    """
    required_files = ['method', 'acqp']
    missing = [file for file in required_files if not os.path.isfile(os.path.join(path, file))]
    pdata_path = os.path.join(path, 'pdata')
    if not os.path.isdir(pdata_path):
        missing.append("pdata folder")
    else:
        subfolders = [f for f in os.listdir(pdata_path) if os.path.isdir(os.path.join(pdata_path, f))]
        if not subfolders:
            missing.append("subfolder within pdata")
        else:
            subfolder_path = os.path.join(pdata_path, subfolders[0])
            if not os.path.isfile(os.path.join(subfolder_path, '2dseq')):
                missing.append("2dseq file within pdata subfolder")
    return missing

def validate_double_angle(directory, theta_path, two_theta_path):
    """
    Check flip angles to make sure it's really double angle method.
    """
    exp_theta = bruker.ReadExperiment(directory, theta_path)
    exp_two_theta = bruker.ReadExperiment(directory, two_theta_path)
    theta = exp_theta.acqp['ACQ_flip_angle']
    two_theta = exp_two_theta.acqp['ACQ_flip_angle']
    if 2*theta != two_theta:
        return True, theta, two_theta
    elif two_theta < 90
        return True, theta, two_theta
    else:
        return False, theta, two_theta

def validate_fp_quesp(directory, quesp_path, t1_path):
    """
    Check to make sure the sequence is actually fp_EPI.
    """ 
    exp_quesp = bruker.ReadExperiment(directory, quesp_path)
    exp_t1 = bruker.ReadExperiment(directory, t1_path)
    check_quesp = exp_quesp.method['Method']
    check_t1 = exp_t1.method['Method']
    if check_quesp != "<User:fp_EPI>" or check_t1 != "<Bruker:RAREVTR>":
        return True, check_quesp, check_t1 
    else:
        return False, check_quesp, check_t1

def validate_mrf(directory, mrf_path):
    """
    Check to make sure the sequece is actually fp_EPI.
    """
    exp_mrf = bruker.ReadExperiment(directory, mrf_path)
    check_mrf = exp_mrf.method['Method']
    if check_mrf != "<User:fp_EPI>":
        return True, check_mrf
    else:
        return False, check_mrf