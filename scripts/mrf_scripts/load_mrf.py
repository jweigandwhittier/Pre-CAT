#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 30 11:42:34 2025

@author: jonah
"""
import numpy as np
import os
import scripts.BrukerMRI as bruker
import pypulseq as pp
import streamlit as st
from custom import st_functions

def generate_dictionary(cfg):
	from cest_mrf.dictionary.generation import generate_mrf_cest_dictionary
	with st.spinner("Generating CEST-MRF dictionary. This may take quite some time..."):
		_ = generate_mrf_cest_dictionary(seq_fn=cfg['seq_fn'], param_fn=cfg['yaml_fn'], dict_fn=cfg['dict_fn'], num_workers=cfg['num_workers'], axes='xy')

def write_yaml(cfg):
	"""
    Writes the configuration dictionary to a YAML file using the path from the config.
    """
	from cest_mrf.write_scenario import write_yaml_dict
	full_path = cfg['yaml_fn']
	output_dir = os.path.dirname(full_path)
	os.makedirs(output_dir, exist_ok=True)
	write_yaml_dict(cfg, full_path)
	st.success(f"YAML configuration saved to: {full_path}")
	st_functions.message_logging(f"YAML configuration saved to: {full_path}")

def seq_from_method(num, directory, cfg):
	"""
	Create Pypulseq object from method and config file parameters.
	"""
	# Load method file
	data = bruker.ReadExperiment(directory, num)
	method = data.method 
	acqp = data.acqp
	# Create arrays from parameter lists with rounding for Pypulseq
	tp_array = np.round(method['Fp_SatDur'] * 1e-3, 3)
	#td = method['PVM_MagTransInterDelay'] * 1e-3
	td = 0 # Set to 0 for now
	tsat_array = np.round(method['PVM_MagTransPulsNumb'] * (tp_array + td) - td, 3)
	dcsat_array = tp_array / (tp_array + td) if (tp_array + td).all() != 0 else np.zeros_like(tp_array)
	# Create new seq_def dictionary
	seq_defs = {}
	seq_defs['n_pulses'] = method['PVM_MagTransPulsNumb']
	seq_defs['tp'] = tp_array.tolist()
	seq_defs['td'] = td
	seq_defs['Trec'] = np.round(method['Fp_TRDels'], 3).tolist()
	seq_defs['Trec_M0'] = 'NaN'
	seq_defs['M0_offset'] = 'NaN'
	seq_defs['DCsat'] = dcsat_array.tolist()
	seq_defs['offsets_hz'] = np.round(method['Fp_SatOffset'], 3).tolist()
	seq_defs['num_meas'] = len(seq_defs['offsets_hz'])
	seq_defs['Tsat'] = tsat_array.tolist()
	seq_defs['B1pa'] = np.round(method['Fp_SatPows'], 3).tolist()
	seq_defs['B0'] = cfg['b0']
	# Get other parameters
	seq_defs['texc'] = np.round(method['ExcPul'][0] * 1e-3, 3) # Length of excitation pulse [s]
	seq_defs['te'] = np.round(method['EchoTime'] * 1e-3, 3) # Readout time for EPI
	seq_defs['fa'] = acqp['ACQ_flip_angle']
	# Filename to save sequence
	seq_fn = cfg['seq_fn']
	seqid = os.path.splitext(seq_fn)[1][1:]
	seq_defs['seq_id_string'] = seqid
	seq = write_sequence(seq_defs, seq_fn, cfg)
	return seq

def write_sequence(seq_defs, seq_fn, cfg):
	"""
	Create preclinical continous-wave sequence for CEST with simple readout.
	Adapted from code by NV.
	"""
	# Constants 
	GAMMA = cfg['gamma']
	# This is the info for the 2d readout sequence. As gradients etc ar
    # simulated as delay, we can just add a delay afetr the imaging pulse for
    # simulation which has the same duration as the actual sequence
    # the flip angle of the readout sequence:
	exc_pulse = pp.make_block_pulse(seq_defs['fa'] * np.pi / 180, duration = seq_defs['texc'])
	imaging_delay = pp.make_delay(seq_defs['te'])
	# Init sequence
	seq = pp.Sequence()
	# Loop B1s
	for idx, b1 in enumerate(seq_defs['B1pa']):
		if idx > 0:
			delay_duration = np.round(seq_defs['Trec'][idx - 1] - seq_defs['te'], 3)
			seq.add_block(pp.make_delay(delay_duration))
		# Sat pulse
		current_offset_hz = seq_defs['offsets_hz'][idx]
		fa_sat = b1 * GAMMA * seq_defs['tp'][idx]
		# Add pulses
		for n_p in range(seq_defs['n_pulses']):
			if b1 == 0:
				seq.add_block(pp.make_delay(seq_defs['tp'][idx]))
			else:
				sat_pulse = pp.make_block_pulse(fa_sat, duration = seq_defs['tp'][idx], freq_offset = current_offset_hz)
				seq.add_block(sat_pulse)
			if n_p < seq_defs['n_pulses'] - 1:
				seq.add_block(pp.make_delay(seq_defs['td']))
	    # Add acq block
		seq.add_block(exc_pulse)
		seq.add_block(imaging_delay)
		pseudo_adc = pp.make_adc(1, duration=1e-3)
		seq.add_block(pseudo_adc)
		# Add defs to seq
	def_fields = seq_defs.keys()
	for field in def_fields:
		seq.set_definition(field, seq_defs[field])
    # Write seq
	full_path = cfg['seq_fn']
    # Ensure the directory for the file exists
	output_dir = os.path.dirname(full_path)
	os.makedirs(output_dir, exist_ok=True)
    # Write the file
	seq.write(full_path)
	st.success(f"Sequence file saved to: {full_path}")
	st_functions.message_logging(f"Sequence file saved to: {full_path}")