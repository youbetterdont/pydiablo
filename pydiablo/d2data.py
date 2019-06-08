import numpy as np
import pkg_resources


class D2Data(object):
    DATA_PATH = pkg_resources.resource_filename('pydiablo', '/')

    @staticmethod
    def filling_values():
        return None

    def __init__(self, filename, key, usecols=None):
        self.data = np.genfromtxt(self.DATA_PATH + filename, delimiter='\t', names=True, dtype=None,
                                  filling_values=self.filling_values(), usecols=usecols, encoding=None)
        self.idx = dict(zip(self.data[key], range(len(self.data[key]))))

    def get_data(self, key, col):
        return self.data[col][self.idx[key]]
