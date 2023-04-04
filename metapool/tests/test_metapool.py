from unittest import TestCase, main
import pandas as pd
import numpy as np
import numpy.testing as npt
import os
from io import StringIO
from metapool.metapool import (read_plate_map_csv, read_pico_csv,
                               calculate_norm_vol, format_dna_norm_picklist,
                               format_index_picklist,
                               compute_qpcr_concentration,
                               compute_shotgun_pooling_values_eqvol,
                               compute_shotgun_pooling_values_qpcr,
                               compute_shotgun_pooling_values_qpcr_minvol,
                               estimate_pool_conc_vol,
                               format_pooling_echo_pick_list,
                               make_2D_array, combine_dfs,
                               add_dna_conc, compute_pico_concentration,
                               bcl_scrub_name, rc, sequencer_i5_index,
                               reformat_interleaved_to_columns,
                               extract_stats_metadata, sum_lanes,
                               merge_read_counts, read_survival,
                               linear_transform, estimate_read_depth,
                               calculate_iseqnorm_pooling_volumes)


class Tests(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.cp_vals = np.array([[10.14, 7.89, 7.9, 15.48],
                                 [7.86, 8.07, 8.16, 9.64],
                                 [12.29, 7.64, 7.32, 13.74]])

        self.dna_vals = np.array([[10.14, 7.89, 7.9, 15.48],
                                  [7.86, 8.07, 8.16, 9.64],
                                  [12.29, 7.64, 7.32, 13.74]])

        self.qpcr_conc = \
            np.array([[98.14626462, 487.8121413, 484.3480866, 2.183406934],
                      [498.3536649, 429.0839787, 402.4270321, 140.1601735],
                      [21.20533391, 582.9456031, 732.2655041, 7.545145988]])

        self.pico_conc = \
            np.array([[38.4090909, 29.8863636, 29.9242424, 58.6363636],
                      [29.7727273, 30.5681818, 30.9090909, 36.5151515],
                      [46.5530303, 28.9393939, 27.7272727, 52.0454545]])

        path = os.path.dirname(__file__)
        plate_fp = os.path.join(path, 'data/test_plate_map.tsv')
        counts_fp = os.path.join(path, 'data/test_filtered_counts.tsv')
        counts_ps_fp = os.path.join(path, 'data/test_per_sample_fastq.tsv')
        no_blanks_fp = os.path.join(path, 'data/test_no_blanks.tsv')
        blanks_fp = os.path.join(path, 'data/test_blanks.tsv')

        self.plate_df = pd.read_csv(plate_fp, sep=',')
        self.counts_df = pd.read_csv(counts_fp, sep=',')
        self.counts_df_ps = pd.read_csv(counts_ps_fp, sep=',')
        self.no_blanks = pd.read_csv(no_blanks_fp, sep='\t')
        self.blanks = pd.read_csv(blanks_fp, sep='\t')
        self.fp = path

    # def test_compute_shotgun_normalization_values(self):
    #     input_vol = 3.5
    #     input_dna = 10
    #     plate_layout = []
    #     for i in range(4):
    #         row = []
    #         for j in range(4):
    #             row.append({'dna_concentration': 10,
    #                         'sample_id': "S%s.%s" % (i, j)})
    #         plate_layout.append(row)

    #     obs_sample, obs_water = compute_shotgun_normalization_values(
    #         plate_layout, input_vol, input_dna)

    #     exp_sample = np.zeros((4, 4), dtype=np.float)
    #     exp_water = np.zeros((4, 4), dtype=np.float)
    #     exp_sample.fill(1000)
    #     exp_water.fill(2500)

    #     npt.assert_almost_equal(obs_sample, exp_sample)
    #     npt.assert_almost_equal(obs_water, exp_water)

    #     # Make sure that we don't go above the limit
    #     plate_layout[1][1]['dna_concentration'] = 0.25
    #     obs_sample, obs_water = compute_shotgun_normalization_values(
    #         plate_layout, input_vol, input_dna)

    #     exp_sample[1][1] = 3500
    #     exp_water[1][1] = 0

    #     npt.assert_almost_equal(obs_sample, exp_sample)
    #     npt.assert_almost_equal(obs_water, exp_water)
    def test_read_plate_map_csv(self):
        plate_map_csv = \
            'Sample\tRow\tCol\tBlank\tProject Name\n' + \
            'sam1\tA\t1\tFalse\tstudy_1\n' + \
            'sam2\tA\t2\tFalse\tstudy_1\n' + \
            'blank1\tB\t1\tTrue\tstudy_1\n' + \
            'sam3\tB\t2\tFalse\tstudy_1\n'

        plate_map_f = StringIO(plate_map_csv)

        exp_plate_df = pd.DataFrame({'Sample': ['sam1', 'sam2', 'blank1',
                                                'sam3'],
                                     'Row': ['A', 'A', 'B', 'B'],
                                     'Col': [1, 2, 1, 2],
                                     'Project Name': ['study_1', 'study_1',
                                                      'study_1', 'study_1'],
                                     'Well': ['A1', 'A2', 'B1', 'B2'],
                                     'Blank': [False, False, True, False]})

        obs_plate_df = read_plate_map_csv(plate_map_f)

        pd.testing.assert_frame_equal(
            obs_plate_df, exp_plate_df, check_like=True)

    def test_read_plate_map_csv_remove_empty_wells(self):
        plate_map_csv = (
            'Sample\tRow\tCol\tBlank\tProject Name\n'
            'sam1\tA\t1\tFalse\tstudy_1\n'
            'sam2\tA\t2\tFalse\tstudy_1\n'
            'blank1\tB\t1\tTrue\tstudy_1\n'
            '\tC\t1\tFalse\tstudy_1\n'
            '\tD\t1\tFalse\tstudy_1\n'
            '\tE\t1\tFalse\tstudy_1\n'
            'sam3\tB\t2\tFalse\tstudy_1\n'
            '\tD\t2\tFalse\tstudy_1\n')

        plate_map_f = StringIO(plate_map_csv)
        exp = pd.DataFrame({'Sample': ['sam1', 'sam2', 'blank1',
                                       'sam3'],
                            'Row': ['A', 'A', 'B', 'B'],
                            'Project Name': [
                                'study_1', 'study_1', 'study_1', 'study_1'],
                            'Col': [1, 2, 1, 2],
                            'Well': ['A1', 'A2', 'B1', 'B2'],
                            'Blank': [False, False, True, False]})

        with self.assertWarnsRegex(UserWarning,
                                   'This plate map contains 4 empty wells, '
                                   'these will be ignored'):
            obs_plate_df = read_plate_map_csv(plate_map_f)

        pd.testing.assert_frame_equal(
            obs_plate_df, exp, check_like=True)

    def test_read_plate_map_csv_error_repeated_sample_names(self):
        plate_map_csv = \
            'Sample\tRow\tCol\tBlank\n' + \
            'sam1\tA\t1\tFalse\n' + \
            'sam2\tA\t2\tFalse\n' + \
            'blank1\tB\t1\tTrue\n' + \
            'blank1\tB\t4\tTrue\n'

        plate_map_f = StringIO(plate_map_csv)

        with self.assertRaises(Exception):
            read_plate_map_csv(plate_map_f)

    def test_read_plate_map_csv_validate_qiita_sample_names(self):
        qiita_oauth2_conf_fp = os.path.join(
            os.getcwd(), 'qiita.oauth2.cfg.local')

        # Test error
        plate_map_csv = \
            'Sample\tRow\tCol\tBlank\tProject Name\n' + \
            'sam1\tA\t1\tFalse\tstudy_1\n' + \
            'sam2\tA\t2\tFalse\tstudy_1\n' + \
            'BLANK1\tB\t1\tTrue\tstudy_1\n' + \
            'sam3\tB\t2\tFalse\tstudy_1\n'
        with self.assertRaisesRegex(ValueError, "study_1 has 3 missing "
                                    r"samples \(i.e. sam1, sam2, sam3\). Some "
                                    "samples from Qiita: SK"):
            read_plate_map_csv(StringIO(plate_map_csv),
                               qiita_oauth2_conf_fp=qiita_oauth2_conf_fp)

        # Test success
        plate_map_csv = \
            'Sample\tRow\tCol\tBlank\tProject Name\n' + \
            'SKM640183\tA\t1\tFalse\tstudy_1\n' + \
            'SKM7.640188\tA\t2\tFalse\tstudy_1\n' + \
            'BLANK1\tB\t1\tTrue\tstudy_1\n' + \
            'SKD3.640198\tB\t2\tFalse\tstudy_1\n'
        obs = read_plate_map_csv(
            StringIO(plate_map_csv), qiita_oauth2_conf_fp=qiita_oauth2_conf_fp)
        exp = pd.DataFrame({
            'Sample': ['SKM640183', 'SKM7.640188', 'BLANK1', 'SKD3.640198'],
            'Row': ['A', 'A', 'B', 'B'],
            'Project Name': ['study_1', 'study_1', 'study_1', 'study_1'],
            'Col': [1, 2, 1, 2],
            'Well': ['A1', 'A2', 'B1', 'B2'],
            'Blank': [False, False, True, False]})
        pd.testing.assert_frame_equal(obs, exp, check_like=True)

    def test_read_pico_csv(self):
        # Test a normal sheet
        pico_csv = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t3.432
        SPL2\tA2\t4949.000\t3.239
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t4039.000\t2.644

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        exp_pico_df = pd.DataFrame({'Well': ['A1', 'A2', 'B1', 'B2'],
                                    'Sample DNA Concentration':
                                    [3.432, 3.239, 10.016, 2.644]})

        pico_csv_f = StringIO(pico_csv)

        obs_pico_df = read_pico_csv(pico_csv_f)

        pd.testing.assert_frame_equal(
            obs_pico_df, exp_pico_df, check_like=True)

        # Test a sheet that has some ???? zero values
        pico_csv = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t3.432
        SPL2\tA2\t4949.000\t3.239
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t\t?????

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        exp_pico_df = pd.DataFrame({'Well': ['A1', 'A2', 'B1', 'B2'],
                                    'Sample DNA Concentration':
                                    [3.432, 3.239, 10.016, np.nan]})

        pico_csv_f = StringIO(pico_csv)

        obs_pico_df = read_pico_csv(pico_csv_f)

        pd.testing.assert_frame_equal(
            obs_pico_df, exp_pico_df, check_like=True)

    def test_read_pico_csv_spectramax(self):
        # Test a normal sheet
        fp_spectramax = os.path.join(os.path.dirname(__file__), 'data',
                                     'pico_spectramax.txt')

        obs_pico_df = read_pico_csv(fp_spectramax,
                                    plate_reader='SpectraMax_i3x')
        self.assertEqual(obs_pico_df.shape[0], 384)
        self.assertEqual(list(obs_pico_df.columns),
                         ['Well', 'Sample DNA Concentration'])
        # Test Invalid plate_reader error
        with self.assertRaises(ValueError):
            read_pico_csv(fp_spectramax, plate_reader='foo')

    def test_read_pico_csv_spectramax_negfix(self):
        # Tests that Concentration values are clipped
        # to a range of (0,60), eliminating possible
        # negative concentration values.
        fp_spectramax = os.path.join(os.path.dirname(__file__), 'data',
                                     'pico_spectramax.txt')

        obs_pico_df = read_pico_csv(fp_spectramax,
                                    plate_reader='SpectraMax_i3x')
        self.assertEqual(all(obs_pico_df['Sample DNA Concentration'] >= 0),
                         True)

        check_for_neg = pd.read_csv(open(fp_spectramax, encoding='utf-16'),
                                    sep='\t', skiprows=2, skipfooter=15,
                                    engine='python')

        conc_col_name = 'Sample DNA Concentration'
        check_for_neg.rename(columns={'Concentration': conc_col_name,
                                      'Wells': 'Well'}, inplace=True)

        self.assertEqual(any(check_for_neg[conc_col_name] < 0), True)

    def test_calculate_norm_vol(self):
        dna_concs = np.array([[2, 7.89],
                              [np.nan, .0]])

        exp_vols = np.array([[2500., 632.5],
                             [3500., 3500.]])

        obs_vols = calculate_norm_vol(dna_concs)

        np.testing.assert_allclose(exp_vols, obs_vols)

    def test_format_dna_norm_picklist(self):

        exp_picklist = (
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name\t'
            'Destination Well\n'
            'sam1\tWater\t384PP_AQ_BP2_HT\tA1\t2.0\t1000.0\tNormalizedDNA\t'
            'A1\n'
            'sam2\tWater\t384PP_AQ_BP2_HT\tA2\t7.89\t2867.5\tNormalizedDNA\t'
            'A2\n'
            'blank1\tWater\t384PP_AQ_BP2_HT\tB1\tnan\t0.0\tNormalizedDNA\t'
            'B1\n'
            'sam3\tWater\t384PP_AQ_BP2_HT\tB2\t0.0\t0.0\tNormalizedDNA\t'
            'B2\n'
            'sam1\tSample\t384PP_AQ_BP2_HT\tA1\t2.0\t2500.0\tNormalizedDNA\t'
            'A1\n'
            'sam2\tSample\t384PP_AQ_BP2_HT\tA2\t7.89\t632.5\tNormalizedDNA\t'
            'A2\n'
            'blank1\tSample\t384PP_AQ_BP2_HT\tB1\tnan\t3500.0\t'
            'NormalizedDNA\tB1\n'
            'sam3\tSample\t384PP_AQ_BP2_HT\tB2\t0.0\t3500.0\tNormalizedDNA\t'
            'B2')

        dna_vols = np.array([[2500., 632.5],
                             [3500., 3500.]])

        water_vols = 3500 - dna_vols

        wells = np.array([['A1', 'A2'],
                          ['B1', 'B2']])

        sample_names = np.array([['sam1', 'sam2'],
                                 ['blank1', 'sam3']])

        dna_concs = np.array([[2, 7.89],
                              [np.nan, .0]])

        obs_picklist = format_dna_norm_picklist(dna_vols, water_vols, wells,
                                                sample_names=sample_names,
                                                dna_concs=dna_concs)

        self.assertEqual(exp_picklist, obs_picklist)

        # test if switching dest wells
        exp_picklist = (
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name\t'
            'Destination Well\n'
            'sam1\tWater\t384PP_AQ_BP2_HT\tA1\t2.0\t1000.0\tNormalizedDNA\t'
            'D1\n'
            'sam2\tWater\t384PP_AQ_BP2_HT\tA2\t7.89\t2867.5\tNormalizedDNA\t'
            'D2\n'
            'blank1\tWater\t384PP_AQ_BP2_HT\tB1\tnan\t0.0\tNormalizedDNA\t'
            'E1\n'
            'sam3\tWater\t384PP_AQ_BP2_HT\tB2\t0.0\t0.0\tNormalizedDNA\t'
            'E2\n'
            'sam1\tSample\t384PP_AQ_BP2_HT\tA1\t2.0\t2500.0\tNormalizedDNA\t'
            'D1\n'
            'sam2\tSample\t384PP_AQ_BP2_HT\tA2\t7.89\t632.5\tNormalizedDNA\t'
            'D2\n'
            'blank1\tSample\t384PP_AQ_BP2_HT\tB1\tnan\t3500.0\tNormalizedDNA\t'
            'E1\n'
            'sam3\tSample\t384PP_AQ_BP2_HT\tB2\t0.0\t3500.0\tNormalizedDNA\t'
            'E2')

        dna_vols = np.array([[2500., 632.5],
                             [3500., 3500.]])

        water_vols = 3500 - dna_vols

        wells = np.array([['A1', 'A2'],
                          ['B1', 'B2']])
        dest_wells = np.array([['D1', 'D2'],
                               ['E1', 'E2']])
        sample_names = np.array([['sam1', 'sam2'],
                                 ['blank1', 'sam3']])

        dna_concs = np.array([[2, 7.89],
                              [np.nan, .0]])

        obs_picklist = format_dna_norm_picklist(dna_vols, water_vols, wells,
                                                dest_wells=dest_wells,
                                                sample_names=sample_names,
                                                dna_concs=dna_concs)

        self.assertEqual(exp_picklist, obs_picklist)

        # test if switching source plates
        exp_picklist = (
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name\t'
            'Destination Well\n'
            'sam1\tWater\t384PP_AQ_BP2_HT\tA1\t2.0\t1000.0\tNormalizedDNA\t'
            'A1\n'
            'sam2\tWater\t384PP_AQ_BP2_HT\tA2\t7.89\t2867.5\tNormalizedDNA\t'
            'A2\n'
            'blank1\tWater\t384PP_AQ_BP2_HT\tB1\tnan\t0.0\tNormalizedDNA\t'
            'B1\n'
            'sam3\tWater\t384PP_AQ_BP2_HT\tB2\t0.0\t0.0\tNormalizedDNA\t'
            'B2\n'
            'sam1\tSample_Plate1\t384PP_AQ_BP2_HT\tA1\t2.0\t2500.0\t'
            'NormalizedDNA\tA1\n'
            'sam2\tSample_Plate1\t384PP_AQ_BP2_HT\tA2\t7.89\t632.5\t'
            'NormalizedDNA\tA2\n'
            'blank1\tSample_Plate2\t384PP_AQ_BP2_HT\tB1\tnan\t3500.0\t'
            'NormalizedDNA\tB1\n'
            'sam3\tSample_Plate2\t384PP_AQ_BP2_HT\tB2\t0.0\t3500.0\t'
            'NormalizedDNA\tB2')

        dna_vols = np.array([[2500., 632.5],
                             [3500., 3500.]])

        water_vols = 3500 - dna_vols

        wells = np.array([['A1', 'A2'],
                          ['B1', 'B2']])

        sample_names = np.array([['sam1', 'sam2'],
                                 ['blank1', 'sam3']])

        sample_plates = np.array([['Sample_Plate1', 'Sample_Plate1'],
                                  ['Sample_Plate2', 'Sample_Plate2']])

        dna_concs = np.array([[2, 7.89],
                              [np.nan, .0]])

        obs_picklist = format_dna_norm_picklist(dna_vols, water_vols, wells,
                                                sample_names=sample_names,
                                                sample_plates=sample_plates,
                                                dna_concs=dna_concs)

        self.assertEqual(exp_picklist, obs_picklist)

    def test_format_index_picklist(self):
        exp_picklist = (
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Transfer Volume\tIndex Name\t'
            'Index Sequence\tIndex Combo\tDestination Plate Name\t'
            'Destination Well\n'
            'sam1\tiTru5_plate\t384LDV_AQ_B2_HT\tA1\t250\tiTru5_01_A\t'
            'ACCGACAA\t0\tIndexPCRPlate\tA1\n'
            'sam2\tiTru5_plate\t384LDV_AQ_B2_HT\tB1\t250\tiTru5_01_B\t'
            'AGTGGCAA\t1\tIndexPCRPlate\tA2\n'
            'blank1\tiTru5_plate\t384LDV_AQ_B2_HT\tC1\t250\tiTru5_01_C\t'
            'CACAGACT\t2\tIndexPCRPlate\tB1\n'
            'sam3\tiTru5_plate\t384LDV_AQ_B2_HT\tD1\t250\tiTru5_01_D\t'
            'CGACACTT\t3\tIndexPCRPlate\tB2\n'
            'sam1\tiTru7_plate\t384LDV_AQ_B2_HT\tA1\t250\tiTru7_101_01\t'
            'ACGTTACC\t0\tIndexPCRPlate\tA1\n'
            'sam2\tiTru7_plate\t384LDV_AQ_B2_HT\tA2\t250\tiTru7_101_02\t'
            'CTGTGTTG\t1\tIndexPCRPlate\tA2\n'
            'blank1\tiTru7_plate\t384LDV_AQ_B2_HT\tA3\t250\tiTru7_101_03\t'
            'TGAGGTGT\t2\tIndexPCRPlate\tB1\n'
            'sam3\tiTru7_plate\t384LDV_AQ_B2_HT\tA4\t250\tiTru7_101_04\t'
            'GATCCATG\t3\tIndexPCRPlate\tB2')

        sample_wells = np.array(['A1', 'A2', 'B1', 'B2'])

        sample_names = np.array(['sam1', 'sam2', 'blank1', 'sam3'])

        indices = pd.DataFrame({'i5 name': {0: 'iTru5_01_A',
                                            1: 'iTru5_01_B',
                                            2: 'iTru5_01_C',
                                            3: 'iTru5_01_D'},
                                'i5 plate': {0: 'iTru5_plate',
                                             1: 'iTru5_plate',
                                             2: 'iTru5_plate',
                                             3: 'iTru5_plate'},
                                'i5 sequence': {0: 'ACCGACAA', 1: 'AGTGGCAA',
                                                2: 'CACAGACT', 3: 'CGACACTT'},
                                'i5 well': {0: 'A1', 1: 'B1', 2: 'C1',
                                            3: 'D1'},
                                'i7 name': {0: 'iTru7_101_01',
                                            1: 'iTru7_101_02',
                                            2: 'iTru7_101_03',
                                            3: 'iTru7_101_04'},
                                'i7 plate': {0: 'iTru7_plate',
                                             1: 'iTru7_plate',
                                             2: 'iTru7_plate',
                                             3: 'iTru7_plate'},
                                'i7 sequence': {0: 'ACGTTACC', 1: 'CTGTGTTG',
                                                2: 'TGAGGTGT', 3: 'GATCCATG'},
                                'i7 well': {0: 'A1', 1: 'A2', 2: 'A3',
                                            3: 'A4'},
                                'index combo': {0: 0, 1: 1, 2: 2, 3: 3},
                                'index combo seq': {0: 'ACCGACAAACGTTACC',
                                                    1: 'AGTGGCAACTGTGTTG',
                                                    2: 'CACAGACTTGAGGTGT',
                                                    3: 'CGACACTTGATCCATG'}})

        obs_picklist = format_index_picklist(
            sample_names, sample_wells, indices)

        self.assertEqual(exp_picklist, obs_picklist)

    def test_compute_qpcr_concentration(self):
        obs = compute_qpcr_concentration(self.cp_vals)
        exp = self.qpcr_conc

        npt.assert_allclose(obs, exp)

    def test_compute_shotgun_pooling_values_eqvol(self):
        obs_sample_vols = \
            compute_shotgun_pooling_values_eqvol(self.qpcr_conc,
                                                 total_vol=60.0)

        exp_sample_vols = np.zeros([3, 4]) + 60.0/12*1000

        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

    def test_compute_shotgun_pooling_values_eqvol_intvol(self):
        obs_sample_vols = \
            compute_shotgun_pooling_values_eqvol(self.qpcr_conc,
                                                 total_vol=60)

        exp_sample_vols = np.zeros([3, 4]) + 60.0/12*1000

        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

    def test_compute_shotgun_pooling_values_qpcr(self):
        sample_concs = np.array([[1, 12, 400],
                                 [200, 40, 1]])

        exp_vols = np.array([[0, 50000, 6250],
                             [12500, 50000, 0]])

        obs_vols = compute_shotgun_pooling_values_qpcr(sample_concs)

        npt.assert_allclose(exp_vols, obs_vols)

    def test_compute_shotgun_pooling_values_qpcr_minvol(self):
        sample_concs = np.array([[1, 12, 400],
                                 [200, 40, 1]])

        exp_vols = np.array([[100, 100, 4166.6666666666],
                             [8333.33333333333, 41666.666666666, 100]])

        obs_vols = compute_shotgun_pooling_values_qpcr_minvol(sample_concs)

        npt.assert_allclose(exp_vols, obs_vols)

    def test_estimate_pool_conc_vol(self):
        obs_sample_vols = compute_shotgun_pooling_values_eqvol(
            self.qpcr_conc, total_vol=60.0)

        obs_pool_conc, obs_pool_vol = estimate_pool_conc_vol(
            obs_sample_vols, self.qpcr_conc)

        exp_pool_conc = 323.873027979
        exp_pool_vol = 60000.0

        npt.assert_almost_equal(obs_pool_conc, exp_pool_conc)
        npt.assert_almost_equal(obs_pool_vol, exp_pool_vol)

    def test_format_pooling_echo_pick_list(self):
        vol_sample = np.array([[10.00, 10.00, 5.00, 5.00, 10.00, 10.00]])

        header = ['Source Plate Name,Source Plate Type,Source Well,'
                  'Concentration,Transfer Volume,Destination Plate Name,'
                  'Destination Well']

        exp_values = ['1,384LDV_AQ_B2_HT,A1,,10.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A2,,10.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A3,,5.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A4,,5.00,NormalizedDNA,A2',
                      '1,384LDV_AQ_B2_HT,A5,,10.00,NormalizedDNA,A2',
                      '1,384LDV_AQ_B2_HT,A6,,10.00,NormalizedDNA,A2']

        exp_str = '\n'.join(header + exp_values)

        obs_str = format_pooling_echo_pick_list(vol_sample,
                                                max_vol_per_well=26,
                                                dest_plate_shape=[16, 24])
        self.maxDiff = None
        self.assertEqual(exp_str, obs_str)

    def test_format_pooling_echo_pick_list_nan(self):
        vol_sample = np.array([[10.00, 10.00, np.nan, 5.00, 10.00, 10.00]])

        header = ['Source Plate Name,Source Plate Type,Source Well,'
                  'Concentration,Transfer Volume,Destination Plate Name,'
                  'Destination Well']

        exp_values = ['1,384LDV_AQ_B2_HT,A1,,10.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A2,,10.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A3,,0.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A4,,5.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A5,,10.00,NormalizedDNA,A2',
                      '1,384LDV_AQ_B2_HT,A6,,10.00,NormalizedDNA,A2']

        exp_str = '\n'.join(header + exp_values)

        obs_str = format_pooling_echo_pick_list(vol_sample,
                                                max_vol_per_well=26,
                                                dest_plate_shape=[16, 24])
        self.maxDiff = None
        self.assertEqual(exp_str, obs_str)

    def test_make_2D_array(self):
        example_qpcr_df = pd.DataFrame({'Cp': [12, 0, 5, np.nan],
                                        'Pos': ['A1', 'A2', 'A3', 'A4']})

        exp_cp_array = np.array([[12.0, 0.0, 5.0, np.nan]])

        np.testing.assert_allclose(make_2D_array(
            example_qpcr_df, rows=1, cols=4).astype(float), exp_cp_array)

        example2_qpcr_df = pd.DataFrame({'Cp': [12, 0, 1, np.nan,
                                                12, 0, 5, np.nan],
                                         'Pos': ['A1', 'A2', 'A3', 'A4',
                                                 'B1', 'B2', 'B3', 'B4']})
        exp2_cp_array = np.array([[12.0, 0.0, 1.0, np.nan],
                                  [12.0, 0.0, 5.0, np.nan]])

        np.testing.assert_allclose(make_2D_array(
            example2_qpcr_df, rows=2, cols=4).astype(float), exp2_cp_array)

    def combine_dfs(self):
        test_index_picklist_f = (
            '\tWell Number\tPlate\tSample Name\tSource Plate Name\t'
            'Source Plate Type\tCounter\tPrimer\tSource Well\tIndex\t'
            'Unnamed: 9\tUnnamed: 10\tUnnamed: 11\tTransfer volume\t'
            'Destination Well\tUnnamed: 14\n'
            '0\t1\tABTX_35\t8_29_13_rk_rh\ti5 Source Plate\t384LDV_AQ_B2_HT\t'
            '1841.0\tiTru5_01_G\tG1\tGTTCCATG\tiTru7_110_05\tA23\tCGCTTAAC\t'
            '250\tA1\tNaN\n'
            '1\t2\tABTX_35\t8_29_13_rk_lh\ti5 Source Plate\t384LDV_AQ_B2_HT\t'
            '1842.0\tiTru5_01_H\tH1\tTAGCTGAG\tiTru7_110_06\tB23\tCACCACTA\t'
            '250\tC1\tNaN\n'
            '2\t1\tABTX_35\t8_29_13_rk_rh\ti7 Source Plate\t384LDV_AQ_B2_HT\t'
            '1841.0\tiTru7_110_05\tA23\tCGCTTAAC\t\t\t\t250\tA1\tNaN\n'
            '3\t2\tABTX_35\t8_29_13_rk_lh\ti7 Source Plate\t384LDV_AQ_B2_HT\t'
            '1842.0\tiTru7_110_06\tB23\tCACCACTA\t\t\t\t250\tC1\tNaN')

        test_dna_picklist_f = (
            '\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name\t'
            'Destination Well\n'
            '0\twater\t384LDV_AQ_B2_HT\tA1\tNaN\t3420.0\tNormalizedDNA\tA1\n'
            '1\twater\t384LDV_AQ_B2_HT\tC1\tNaN\t3442.5\tNormalizedDNA\tC1\n'
            '5\t1\t384LDV_AQ_B2_HT\tA1\t12.751753\t80.0\tNormalizedDNA\tA1\n'
            '6\t1\t384LDV_AQ_B2_HT\tC1\t17.582063\t57.5\tNormalizedDNA\tC1')

        test_qpcr_f = (
            '\tInclude\tColor\tPos\tName\tCp\tConcentration\tStandard\tStatus'
            '0\tTRUE\t255\tA1\tSample 1\t20.55\tNaN\t0\tNaN'
            '1\tTRUE\t255\tC1\tSample 2\t9.15\tNaN\t0\tNaN')

        exp_out_f = (
            'Well\tCp\tDNA Concentration\tDNA Transfer Volume\tSample Name\t'
            'Plate\tCounter\tPrimer i7\tSource Well i7\tIndex i7\tPrimer i5\t'
            'Source Well i5\tIndex i5'
            'A1\t20.55\t12.751753\t80.0\t8_29_13_rk_rh\tABTX_35\t1841.0\t'
            'iTru7_110_05\tA23\tCGCTTAAC\tiTru5_01_G\tG1\tGTTCCATG'
            'C1\t9.15\t17.582063\t57.5\t8_29_13_rk_lh\tABTX_35\t1842.0\t'
            'iTru7_110_06\tB23\tCACCACTA\tiTru5_01_H\tH1\tTAGCTGAG')

        test_index_picklist_df = pd.read_csv(
            StringIO(test_index_picklist_f), header=0, sep='\t')
        test_dna_picklist_df = pd.read_csv(
            StringIO(test_dna_picklist_f), header=0, sep='\t')
        test_qpcr_df = pd.read_csv(StringIO(test_qpcr_f), header=0, sep='\t')

        exp_df = pd.read_csv(StringIO(exp_out_f), header=0, sep='\t')

        combined_df = combine_dfs(
            test_qpcr_df, test_dna_picklist_df, test_index_picklist_df)

        pd.testing.assert_frame_equal(combined_df, exp_df, check_like=True)

    def test_add_dna_conc(self):
        test_dna = 'Well\tpico_conc\nA1\t2.5\nC1\t20'

        test_combined = (
            'Well\tCp\tDNA Concentration\tDNA Transfer Volume\tSample Name'
            '\tPlate\tCounter\tPrimer i7\tSource Well i7\tIndex i7\tPrimer i5'
            '\tSource Well i5\tIndex i5\n'
            'A1\t20.55\t12.751753\t80.0\t8_29_13_rk_rh\tABTX_35\t1841.0\t'
            'iTru7_110_05\tA23\tCGCTTAAC\tiTru5_01_G\tG1\tGTTCCATG\n'
            'C1\t9.15\t17.582063\t57.5\t8_29_13_rk_lh\tABTX_35\t1842.0\t'
            'iTru7_110_06\tB23\tCACCACTA\tiTru5_01_H\tH1\tTAGCTGAG')

        test_exp_out = (
            'Well\tCp\tDNA Concentration\tDNA Transfer Volume\t'
            'Sample Name\tPlate\tCounter\tPrimer i7\tSource Well i7\tIndex i7'
            '\tPrimer i5\tSource Well i5\tIndex i5\tpico_conc\n'
            'A1\t20.55\t12.751753\t80.0\t8_29_13_rk_rh\tABTX_35\t1841.0\t'
            'iTru7_110_05\tA23\tCGCTTAAC\tiTru5_01_G\tG1\tGTTCCATG\t2.5\n'
            'C1\t9.15\t17.582063\t57.5\t8_29_13_rk_lh\tABTX_35\t1842.0\t'
            'iTru7_110_06\tB23\tCACCACTA\tiTru5_01_H\tH1\tTAGCTGAG\t20')

        exp_df = pd.read_csv(StringIO(test_exp_out), header=0, sep='\t')
        test_in_df = pd.read_csv(StringIO(test_combined), header=0, sep='\t')
        test_dna_df = pd.read_csv(StringIO(test_dna), header=0, sep='\t')

        obs_df = add_dna_conc(test_in_df, test_dna_df)

        pd.testing.assert_frame_equal(obs_df, exp_df, check_like=True)

    def test_compute_pico_concentration(self):
        obs = compute_pico_concentration(self.dna_vals)
        exp = self.pico_conc

        npt.assert_allclose(obs, exp)

    def test_bcl_scrub_name(self):
        self.assertEqual('test_1', bcl_scrub_name('test.1'))
        self.assertEqual('test-1', bcl_scrub_name('test-1'))
        self.assertEqual('test_1', bcl_scrub_name('test_1'))

    def test_rc(self):
        self.assertEqual(rc('AGCCT'), 'AGGCT')

    def test_sequencer_i5_index(self):
        indices = ['AGCT', 'CGGA', 'TGCC']

        exp_rc = ['AGCT', 'TCCG', 'GGCA']

        obs_hiseq4k = sequencer_i5_index('HiSeq4000', indices)
        obs_hiseq25k = sequencer_i5_index('HiSeq2500', indices)
        obs_nextseq = sequencer_i5_index('NextSeq', indices)

        self.assertListEqual(obs_hiseq4k, exp_rc)
        self.assertListEqual(obs_hiseq25k, indices)
        self.assertListEqual(obs_nextseq, exp_rc)

        with self.assertRaises(ValueError):
            sequencer_i5_index('foo', indices)

    def test_reformat_interleaved_to_columns(self):
        wells = ['A1', 'A23', 'C1', 'C23',
                 'A2', 'A24', 'C2', 'C24',
                 'B1', 'B23', 'D1', 'D23',
                 'B2', 'B24', 'D2', 'D24']

        exp = ['A1', 'B6', 'C1', 'D6',
               'A7', 'B12', 'C7', 'D12',
               'A13', 'B18', 'C13', 'D18',
               'A19', 'B24', 'C19', 'D24']

        obs = reformat_interleaved_to_columns(wells)

        np.testing.assert_array_equal(exp, obs)

    def test_extract_stats_metadata_plus_sum_lanes_single_lane(self):
        fp = 'notebooks/test_data/Demux/Stats.json'
        obs_lm, obs_df, obs_unk = extract_stats_metadata(fp, [5])

        # test legacy, degenerate case of summing one lane.
        obs_df = sum_lanes(obs_df, [5])
        obs_unk = sum_lanes(obs_unk, [5])

        exp_lm = {"Flowcell": "HLHWHBBXX",
                  "RunNumber": 458,
                  "RunId": "171006_K00180_0458_AHLHWHBBXX_RKL003_FinRisk_17_48"
                  }
        # compare lane metadata
        self.assertDictEqual(obs_lm, exp_lm)

        # compare data-frames (first row and last row only)
        obs_fr = obs_df.iloc[[0]].to_dict(orient='records')[0]
        obs_lr = obs_df.iloc[[-1]].to_dict(orient='records')[0]

        exp_fr = {
            "Mismatch0": 137276,
            "Mismatch1": 6458,
            "NumberReads": 143734,
            "YieldR1": 21703834,
            "YieldQ30R1": 19772948,
            "YieldR2": 21703834,
            "YieldQ30R2": 17555284,
            "Yield": 43407668
        }

        exp_lr = {
            "Mismatch0": 894502,
            "Mismatch1": 42048,
            "NumberReads": 936550,
            "YieldR1": 141419050,
            "YieldQ30R1": 126289116,
            "YieldR2": 141419050,
            "YieldQ30R2": 116636541,
            "Yield": 282838100
        }
        self.assertDictEqual(obs_fr, exp_fr)
        self.assertDictEqual(obs_lr, exp_lr)

        # compare unknown barcodes output (first row and last row only)
        obs_fr = obs_unk.iloc[[0]].to_dict(orient='records')[0]
        obs_lr = obs_unk.iloc[[-1]].to_dict(orient='records')[0]

        exp_fr = {
            "Mismatch0": 137276,
            "Mismatch1": 6458,
            "NumberReads": 143734,
            "YieldR1": 21703834,
            "YieldQ30R1": 19772948,
            "YieldR2": 21703834,
            "YieldQ30R2": 17555284,
            "Yield": 43407668
        }

        exp_lr = {
            "Mismatch0": 894502,
            "Mismatch1": 42048,
            "NumberReads": 936550,
            "YieldR1": 141419050,
            "YieldQ30R1": 126289116,
            "YieldR2": 141419050,
            "YieldQ30R2": 116636541,
            "Yield": 282838100
        }
        self.assertDictEqual(obs_fr, {"Value": 67880})
        self.assertDictEqual(obs_lr, {"Value": 2440})

    def test_extract_stats_metadata_plus_sum_lanes_two_lanes(self):
        fp = 'notebooks/test_data/Demux/OverlapSeqStats.json'
        _, obs_df, obs_unk = extract_stats_metadata(fp, [5, 1])

        # test legacy, degenerate case of summing one lane.
        obs_df = sum_lanes(obs_df, [5, 1])
        obs_unk = sum_lanes(obs_unk, [5, 1])

        # compare data-frames
        obs_fr = obs_df.iloc[[0]].to_dict(orient='records')[0]
        obs_lr = obs_df.iloc[[-1]].to_dict(orient='records')[0]

        exp_fr = {
            "Mismatch0": 6917044,
            "Mismatch1": 452990,
            "NumberReads": 7376278,
            "YieldR1": 1106441700,
            "YieldQ30R1": 875757969,
            "YieldR2": 1106441700,
            "YieldQ30R2": 676057515,
            "Yield": 2212883400
        }
        exp_lr = {
            "Mismatch0": 5075088,
            "Mismatch1": 368852,
            "NumberReads": 16174348,
            "YieldR1": 2426152200,
            "YieldQ30R1": 1913639164,
            "YieldR2": 2426152200,
            "YieldQ30R2": 1472852479,
            "Yield": 4852304400
        }

        self.assertDictEqual(obs_fr, exp_fr)
        self.assertDictEqual(obs_lr, exp_lr)

        # compare unknown barcodes output (first row and last row only)
        obs_fr = obs_unk.iloc[[0]].to_dict(orient='records')[0]
        obs_lr = obs_unk.iloc[[-1]].to_dict(orient='records')[0]

        exp_fr = {
            "Value": 5103.0
        }
        exp_lr = {
            "Value": 6336.0
        }

        self.assertDictEqual(obs_fr, exp_fr)
        self.assertDictEqual(obs_lr, exp_lr)

    def test_merge_read_counts(self):

        # TEST EXCEPTION UNSUPPORTED FILE TYPE
        counts_df = self.counts_df.copy()
        counts_df.rename(columns={'Category': 'nope'}, inplace=True)
        with self.assertRaisesRegex(Exception,
                                    'Unsupported input file type.'):
            merge_read_counts(self.plate_df,
                              counts_df,
                              reads_column_name='Filtered Reads')

        # TEST ID NOT FOUND
        counts_df = self.counts_df.copy()
        n = len(counts_df)
        counts_df['Category'] = ['a' for i in range(n)]
        with self.assertRaisesRegex(LookupError,
                                    'id not found in a'):
            merge_read_counts(self.plate_df,
                              counts_df,
                              reads_column_name='Filtered Reads')

        # TEST CORRECT OUTPUT WITH FastQC
        exp_fp = os.path.join(self.fp, 'data/test_output_merge.tsv')
        exp = pd.read_csv(exp_fp, sep='\t')
        obs = merge_read_counts(self.plate_df, self.counts_df)
        pd.testing.assert_frame_equal(exp, obs)

        # TEST CORRECT OUTPUT WITH per_sample_FASTQ
        exp_fp = os.path.join(self.fp, 'data/test_output_merge_ps.tsv')
        exp = pd.read_csv(exp_fp, sep='\t')
        obs = merge_read_counts(self.plate_df, self.counts_df_ps)
        pd.testing.assert_frame_equal(exp, obs)

    def test_read_survival(self):

        reads = [10 + i for i in range(11)]
        reads = pd.DataFrame({'reads': reads})

        counts = [11.0, 11.0, 11.0, 9.0, 5.0]
        index = [0, 4, 8, 12, 16]
        exp = pd.DataFrame({'Remaining': counts}, index=index)
        obs = read_survival(reads, label='Remaining',
                            rmin=0, rmax=20, rsteps=5)
        pd.testing.assert_frame_equal(exp, obs)

    def test_linear_transform(self):

        counts = range(5)
        index = range(5)
        counts = pd.Series(counts, index=index)
        obs = linear_transform(counts, output_min=0, output_max=40)
        exp = [float(i) for i in range(0, 50, 10)]
        exp = pd.Series(exp, index=index)
        pd.testing.assert_series_equal(obs, exp)

    def test_calculate_iseqnorm_pooling_volumes(self):

        # TEST MATH IS CORRECT & WARNS NO BLANKS
        with self.assertWarnsRegex(UserWarning,
                                   'There are no BLANKS in this plate'):
            obs = calculate_iseqnorm_pooling_volumes(self.no_blanks)
        exp_fp = os.path.join(self.fp, 'data/test_no_blanks_output.tsv')
        exp = pd.read_csv(exp_fp, sep='\t')
        pd.testing.assert_frame_equal(obs, exp)

        # TEST BLANKS ARE HANDLED CORRECTLY
        obs = calculate_iseqnorm_pooling_volumes(self.blanks)
        exp_fp = os.path.join(self.fp, 'data/test_blanks_output.tsv')
        exp = pd.read_csv(exp_fp, sep=',')
        pd.testing.assert_frame_equal(obs, exp)

    def test_estimate_read_depth(self):

        raw_fp = os.path.join(self.fp, 'data/test_raw_counts.tsv')
        rawcts_df = pd.read_csv(raw_fp, sep=',')

        frame = merge_read_counts(self.plate_df, self.counts_df)
        frame = merge_read_counts(frame, rawcts_df,
                                  reads_column_name='Raw Reads')
        frame = calculate_iseqnorm_pooling_volumes(frame)

        obs = estimate_read_depth(frame, estimated_total_output=600)
        exp_fp = os.path.join(self.fp, 'data/test_read_depth_output.tsv')
        exp = pd.read_csv(exp_fp, sep='\t')
        pd.testing.assert_frame_equal(exp, obs)


if __name__ == "__main__":
    main()
