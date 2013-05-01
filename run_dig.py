import re

from archaeologit.excavator import excavate

if __name__ == '__main__':
    excavate('/home/edmund/projects/diffscuss',
             '/home/edmund/tmp/archout',
             interesting_fnames_res=[],
             boring_fnames_res=[],
             fact_finders=[],
             num_procs=4)


