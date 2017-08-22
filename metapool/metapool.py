import os
import numpy as np
import pandas as pd
import string
import seaborn as sns
import matplotlib.pyplot as plt
from io import StringIO

def compute_qpcr_concentration(cp_vals, m=-3.231, b=12.059, dil_factor=25000):
    """Computes molar concentration of libraries from qPCR Cp values.

    Returns a 2D array of calculated concentrations, in nanomolar units

    Parameters
    ----------
    cp_vals : numpy array of float
        The Cp values parsed from the plate reader
    m : float
        The slope of the qPCR standard curve
    b : float
        The intercept of the qPCR standard curve
    dil_factor: float or int
        The dilution factor of the samples going into the qPCR

    Returns
    -------10
    np.array of floats
        A 2D array of floats
    """
    qpcr_concentration = np.power(10, ((cp_vals - b) / m)) * dil_factor / 1000

    return(qpcr_concentration)


def compute_shotgun_pooling_values_eqvol(sample_concs, total_vol=60.0):
    """Computes molar concentration of libraries from qPCR Cp values.

    Returns a 2D array of calculated concentrations, in nanomolar units

    Parameters
    ----------
    sample_concs : numpy array of float
        The concentrations calculated via qPCR (nM)
    total_vol : float
        The total volume to pool (uL)

    Returns
    -------
    np.array of floats
        A 2D array of floats
    """
    per_sample_vol = (total_vol / sample_concs.size) * 1000.0

    sample_vols = np.zeros(sample_concs.shape) + per_sample_vol

    return(sample_vols)


def compute_shotgun_pooling_values_qpcr(sample_concs, sample_fracs=None,
                                        min_conc=10, floor_conc=50,
                                        total_nmol=.01):
    """Computes pooling volumes for samples based on qPCR estimates of
    nM concentrations (`sample_concs`).

    Reads in qPCR values in nM from output of `compute_qpcr_concentration`.
    Samples must be above a minimum concentration threshold (`min_conc`,
    default 10 nM) to be included. Samples above this threshold but below a
    given floor concentration (`floor_conc`, default 50 nM) will be pooled as
    if they were at the floor concentration, to avoid overdiluting the pool.

    Samples can be assigned a target molar fraction in the pool by passing a
    np.array (`sample_fracs`, same shape as `sample_concs`) with fractional
    values per sample. By default, will aim for equal molar pooling.

    Finally, total pooling size is determined by a target nanomolar quantity
    (`total_nmol`, default .01). For a perfect 384 sample library, in which you
    had all samples at a concentration of exactly 400 nM and wanted a total
    volume of 60 uL, this would be 0.024 nmol.

    Parameters
    ----------
    sample_concs: 2D array of float
        nM calculated by compute_qpcr_concentration
    sample_fracs: 2D of float
        fractional value for each sample (default 1/N)
    min_conc: float
        minimum nM concentration to be included in pool
    floor_conc: float
        minimum value for pooling for samples above min_conc
        corresponds to a maximum vol in pool
    total_nmol : float
        total number of nM to have in pool

    Returns
    -------
    sample_vols: np.array of floats
        the volumes in nL per each sample pooled
    """

    if sample_fracs is None:
        sample_fracs = np.ones(sample_concs.shape) / sample_concs.size

    # get samples above threshold
    sample_fracs_pass = sample_fracs.copy()
    sample_fracs_pass[sample_concs <= min_conc] = 0

    # renormalize to exclude lost samples
    sample_fracs_pass *= 1/sample_fracs_pass.sum()

    # floor concentration value
    sample_concs_floor = sample_concs.copy()
    sample_concs_floor[sample_concs < floor_conc] = floor_conc

    # calculate volumetric fractions including floor val
    sample_vols = (total_nmol * sample_fracs_pass) / sample_concs_floor

    # convert L to nL
    sample_vols *= 10**9

    return(sample_vols)


def estimate_pool_conc_vol(sample_vols, sample_concs):
    """Estimates the actual molarity and volume of a pool.

    Parameters
    ----------
    sample_concs : numpy array of float
        The concentrations calculated via qPCR (nM)
    sample_vols : numpy array of float
        The calculated pooling volumes (nL)

    Returns
    -------
    pool_conc : float
        The estimated actual concentration of the pool, in nM
    total_vol : float
        The total volume of the pool, in nL
    """
    # scalar to adjust nL to L for molarity calculations
    nl_scalar = 10**-9

    # calc total pool pmols
    total_pmols = np.multiply(sample_concs, sample_vols) * nl_scalar

    # calc total pool vol in nanoliters
    total_vol = sample_vols.sum()

    # pool pM is total pmols divided by total liters
    # (total vol in nL * 1 L / 10^9 nL)
    pool_conc = total_pmols.sum() / (total_vol * nl_scalar)

    return(pool_conc, total_vol)

def format_pooling_echo_pick_list(vol_sample,
                                  max_vol_per_well=60000,
                                  dest_plate_shape=[16,24]):
    """Format the contents of an echo pooling pick list

    Parameters
    ----------
    vol_sample : 2d numpy array of floats
        The per well sample volume, in nL
    max_vol_per_well : 2d numpy array of floats
        Maximum destination well volume, in nL
    """
    contents = ['Source Plate Name,Source Plate Type,Source Well,'
                'Concentration,Transfer Volume,Destination Plate Name,'
                'Destination Well']
    # Write the sample transfer volumes
    rows, cols = vol_sample.shape

    running_tot = 0
    d = 1
    for i in range(rows):
        for j in range(cols):
            well_name = "%s%d" % (chr(ord('A') + i), j+1)
            # Machine will round, so just give it enough info to do the
            # correct rounding.
            val = "%.2f" % vol_sample[i][j]

            # test to see if we will exceed total vol per well
            if running_tot + vol_sample[i][j] > max_vol_per_well:
                d += 1
                running_tot = vol_sample[i][j]
            else:
                running_tot += vol_sample[i][j]

            dest = "%s%d" % (chr(ord('A') +
                             int(np.floor(d/dest_plate_shape[0]))),
                             (d % dest_plate_shape[1]))

            contents.append(
                ",".join(['1', '384LDV_AQ_B2_HT', well_name, "",
                          val, 'NormalizedDNA', dest]))

    return "\n".join(contents)

def plot_plate_vals(dataset, color_map='YlGnBu', annot_str=None,
                    annot_fmt='.5s'):
    """
    Plots values in a plate format. Returns a heatmap in the shape of the
    plate, with bar graphs aligned to the rows and columns showing the mean and
    spread of each row and column, and a histogram showing the distribution of
    values.

    Optionally can plot an array of names or other annotations on top of the
    heatmap.

    Parameters
    ----------
    dataset: 2D array of numeric
        data to plot
    color_map: str
        matplotlib color map name for heatmap
    annot_str: 2D array of str
        values to write over heatmap values to annotate wells
    annot_fmt: str
        string formatting values for annotations. Defaults to first 5 char per
        well.

    Returns
    -------
    """
    fig = plt.figure(figsize=(20,20))


    with sns.axes_style("white"):
        ax1 = plt.subplot2grid((40,20), (20,0), colspan=18, rowspan=18)
        ax1.xaxis.tick_top()
        if annot_str is None:
            sns.heatmap(dataset,
                        ax=ax1,
                        xticklabels = [x + 1 for x in range(24)],
                        yticklabels = list(string.ascii_uppercase)[0:16],
                        #square = True,
                        annot = True,
                        fmt = '.0f',
                        cmap = color_map,
                        cbar = False)
        else:
            sns.heatmap(dataset,
                        ax=ax1,
                        xticklabels = [x + 1 for x in range(24)],
                        yticklabels = list(string.ascii_uppercase)[0:16],
                        #square = True,
                        annot = annot_str,
                        fmt = annot_fmt,
                        cmap = color_map,
                        cbar = False)

    with sns.axes_style("white"):
        ax2 = plt.subplot2grid((40,20), (38,0), colspan=18, rowspan=2)
        ax3 = plt.subplot2grid((40,20), (20,18), colspan=2, rowspan=18)
        sns.despine()
        sns.barplot(data=dataset, orient='v', ax=ax2, color = 'grey')
        sns.barplot(data=dataset.transpose(), orient='h', ax=ax3,
                    color = 'grey')
        ax2.set(xticklabels=[], yticklabels=[])
        ax3.set(xticklabels=[], yticklabels=[])

    with sns.axes_style():
        ax4 = plt.subplot2grid((40,20), (0,0), colspan=18, rowspan=18)
        sns.distplot(dataset.flatten()[~np.isnan(dataset.flatten())], ax=ax4,
                     bins = 20)

    return

def make_2D_array(qpcr, data_col='Cp', well_col='Pos', rows=16, cols=24):
    """
    Pulls a column of data out of a dataframe and puts into array format
    based on well IDs in another column

    Parameters
    ----------
    qpcr: Pandas DataFrame
        dataframe from which to pull values
    data_col: str
        name of column with data
    well_col: str
        name of column with well IDs, in 'A1,B12' format
    rows: int
        number of rows in array to return
    cols: int
        number of cols in array to return

    Returns
    -------
    """
    # initialize empty Cp array
    cp_array = np.empty((rows,cols), dtype=object)

    # fill Cp array with the post-cleaned values from the right half of the
    # plate
    for record in qpcr.iterrows():
        row = ord(str.upper(record[1][well_col][0])) - ord('A')
        col = int(record[1][well_col][1:]) - 1
        cp_array[row,col] = record[1][data_col]

    return(cp_array)


def combine_dfs(qpcr_df, dna_picklist, index_picklist):
    """
    Combines information from the three dataframes into a single frame suitable
    for plotting

    Parameters
    ----------
    qpcr_df: Pandas DataFrame
        df from qpcr data import. Expects cols ['Pos','Cp']
    dna_picklist: Pandas DataFrame
        df from DNA picklist import. Expects cols
        ['Destination Well', 'Concentration', 'Transfer Volume']
    index_picklist: Pandas DataFrame
        df from index addition picklist import. Expects cols
        ['Destination Well','Plate','Sample Name',
         'Counter','Primer','Source Well','Index']

    Returns
    -------
    combined_df: Pandas DataFrame
        new DataFrame with the relevant columns
    """
    combined_df = pd.DataFrame({'Well': qpcr_df['Pos'],
                                'Cp': qpcr_df['Cp']})

    combined_df.set_index('Well', inplace=True)

    b = dna_picklist.loc[dna_picklist['Source Plate Name'] != 'water',
                         ].set_index('Destination Well')
    c = index_picklist.loc[index_picklist['Source Plate Name'] ==
                           'i7 Source Plate',].set_index('Destination Well')
    d = index_picklist.loc[index_picklist['Source Plate Name'] ==
                           'i5 Source Plate',].set_index('Destination Well')

    # Add DNA conc columns
    combined_df['DNA Concentration'] = b['Concentration']
    combined_df['DNA Transfer Volume'] = b['Transfer Volume']

    # Add Index columns
    combined_df['Sample Name'] = c['Sample Name']
    combined_df['Plate'] = c['Plate']
    combined_df['Counter'] = d['Counter']
    combined_df['Source Well i7'] = c['Source Well']
    combined_df['Index i7'] = c['Index']
    combined_df['Primer i7'] = c['Primer']
    combined_df['Source Well i5'] = d['Source Well']
    combined_df['Index i5'] = d['Index']
    combined_df['Primer i5'] = d['Primer']

    combined_df.reset_index(inplace=True)

    return(combined_df)