from fairmat_readers_xrd import read_rigaku_rasx
from nomad_measurements.utils import AttrDict


def test_hdf5_file_generation():
    # read the example file
    data_dict = read_rigaku_rasx('./tests/xrd/TwoTheta_scan_powder.rasx')
    data_obj = AttrDict(lambda: None, data_dict)

    print(data_obj.metadata.sds)
    print(data_obj.metadat.sds)
    print(data_obj['metadata']['sds'])
    print(data_obj['metadat']['sds'])


if __name__ == '__main__':
    test_hdf5_file_generation()
