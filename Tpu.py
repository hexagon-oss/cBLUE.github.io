import logging
logging.basicConfig(format='%(asctime)s:%(message)s', level=logging.INFO)
import pathos.pools as pp
import json
import os
import numpy as np
import numexpr as ne
import pandas as pd
from collections import OrderedDict

from Las import Las
from Merge import Merge
from Subaerial import Subaerial
from Subaqueous_frt import Subaqueous


class Tpu:

    def __init__(self, subaqueous_metadata, surface_select,
                 surface_ind, wind_selection, wind_val,
                 kd_selection, kd_val, vdatum_region,
                 vdatum_region_mcu, tpu_output, fR, fJ1, fJ2, fJ3, fF):
        self.subaqueous_lookup_params = subaqueous_metadata
        self.surface_select = surface_select
        self.surface_ind = surface_ind
        self.wind_selection = wind_selection
        self.wind_val = wind_val
        self.kdSelect = kd_selection
        self.kd_val = kd_val
        self.vdatum_region = vdatum_region
        self.vdatum_region_mcu = vdatum_region_mcu
        self.tpuOutput = tpu_output
        self.fR = fR
        self.fJ1 = fJ1
        self.fJ2 = fJ2
        self.fJ3 = fJ3
        self.fF = fF
        self.metadata = {}
        self.flight_line_stats = {}
        
    def calc_tpu(self, las, sbet):
        
        data_to_pickle = []
        output_columns = []
        
        las = Las(las)
        logging.info('{}\n{}'.format('#' * 30, las.las_short_name))
        logging.info(las.get_flight_line_ids())

        for fl in las.get_flight_line_ids():
            logging.info('flight line {} {}'.format(fl, '-' * 30))
            D = Merge.merge(las.las_short_name, fl, sbet.values, las.get_flight_line_txyz(fl))

            logging.info('({}) calculating subaerial THU/TVU...'.format(las.las_short_name))
            subaerial, subaerial_columns = Subaerial(D, self.fR).calc_subaerial(
                self.fJ1, self.fJ2, self.fJ3, self.fF)
            depth = subaerial[:, 2] + las.get_average_depth()
            subaerial_thu = subaerial[:, 3]
            subaerial_tvu = subaerial[:, 4]
            logging.info('({}) calculating subaqueous THU/TVU...'.format(las.las_short_name))
            subaqueous_thu, subaqueous_tvu, subaqueous_columns = Subaqueous.main(
                self.surface_ind, self.wind_val, self.kd_val, depth)

            vdatum_mcu = float(self.vdatum_region_mcu) / 100.0  # file is in cm (1-sigma)

            logging.info('({}) calculating total THU...'.format(las.las_short_name))
            total_thu = ne.evaluate('sqrt(subaerial_thu**2 + subaqueous_thu**2)')

            logging.info('({}) calculating total TVU...'.format(las.las_short_name))
            total_tvu = ne.evaluate('sqrt(subaqueous_tvu**2 + subaerial_tvu**2 + vdatum_mcu**2)')
            num_points = total_tvu.shape[0]
            output = np.hstack((
                np.round_(subaerial, decimals=5),
                np.round_(np.expand_dims(subaqueous_thu, axis=1), decimals=5),
                np.round_(np.expand_dims(subaqueous_tvu, axis=1), decimals=5),
                np.round_(np.expand_dims(total_thu, axis=1), decimals=5),
                np.round_(np.expand_dims(total_tvu, axis=1), decimals=5),
                ))

            sigma_columns = ['total_thu', 'total_tvu']
            output_columns = subaerial_columns + subaqueous_columns + sigma_columns  # TODO: doesn't need to happen every iteration
            data_to_pickle.append(output)
            stats = ['min', 'max', 'mean', 'std']
            self.flight_line_stats[str(fl)] = pd.DataFrame(
                output, columns=output_columns).describe().loc[stats].to_dict()

        self.write_metadata(las)  # TODO: include as VLR?
        #self.output_tpu_to_las()
        self.output_tpu_to_pickle(las, data_to_pickle, output_columns)

    def output_tpu_to_pickle(self, las, data_to_pickle, output_columns):
        output_tpu_file = r'{}_TPU.tpu'.format(las.las_base_name)
        output_path = '{}\\{}'.format(self.tpuOutput, output_tpu_file)
        output_df = pd.DataFrame(np.vstack(data_to_pickle), columns=output_columns)
        logging.info('({}) writing TPU...'.format(las.las_short_name))
        output_df.to_pickle(output_path)
        logging.info('finished writing')

    def output_tpu_to_las(self, las, data_to_pickle):
        in_las = laspy.file.File(las, mode = "r")
        out_las_name = las.replace('.las', '_TPU.las')
        out_las = laspy.file.File(out_las_name, mode="w", header=in_las.header)

        output_data_indexes = {
            'subaerial_thu': 3,
            'subaerial_tvu': 4,
            'subaqueous_thu': 5,
            'subaqueous_tvu': 6,
            'total_thu': 7,
            'total_tvu': 8,
            }

        extra_byte_dimensions = OrderedDict([
            ('subaerial_thu', 'subaerial total propagated vertical uncertainty'),
            ('subaerial_tvu', 'subaerial total propagated horizontal uncertainty'),
            ('subaqueous_thu', 'subaqueous total propagated vertical uncertainty'),
            ('subaqueous_tvu', 'subaqueous total propagated horizontal uncertainty'),
            ('total_thu', 'subaerial and subaqueous tvu combined in quadrature'),
            ('total_tvu', 'subaerial and subaqueous thu combined in quadrature')
            ])

        # define and populate new extrabyte dimensions
        for dimension, description in extra_byte_dimensions.iteritems():
            out_las.define_new_dimension(name=dimension, data_type=5, description=description)
            exec('outFile.{} = tpu_results[{}]'.format(dimension, output_data_indexes[dimension]))

        # copy data from in_las
        for field in in_las.point_format:
            print('writing {} to {} ...'.format(field.name, out_las))
            dat = in_las.reader.get_dimension(field.name)
            out_las.writer.set_dimension(field.name, dat)

    def write_metadata(self, las):
        logging.info('({}) creating TPU meta data file...'.format(las.las_short_name))
        self.metadata.update({
            'subaqueous lookup params': self.subaqueous_lookup_params,
            'water surface': self.surface_select,
            'wind': self.wind_selection,
            'kd': self.kdSelect,
            'VDatum region': self.vdatum_region,
            'VDatum region MCU': self.vdatum_region_mcu,
            'flight line stats': {}
        })

        try:
            self.metadata['flight line stats'].update(self.flight_line_stats)  # flight line metadata
            with open(os.path.join(self.tpuOutput, '{}.json'.format(las.las_base_name)), 'w') as outfile:
                json.dump(self.metadata, outfile, indent=1, ensure_ascii=False)
        except Exception, e:
            print(e)

    def run_tpu_multiprocessing(self, las_files, sbet_files):
        p = pp.ProcessPool(4)
        p.imap(self.calc_tpu, las_files, sbet_files)
        p.close()
        p.join()
        

if __name__ == '__main__':
    pass