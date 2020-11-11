#!/usr/bin/env python

""" MultiQC module to parse output from odgi stats """

from __future__ import print_function
import logging
import sys
from collections import OrderedDict

from multiqc.modules.base_module import BaseMultiqcModule
from multiqc.plots import linegraph

# Initialise the logger
log = logging.getLogger(__name__)


class MultiqcModule(BaseMultiqcModule):
    """
    The MultiQC module to parse and plot odgi stats
    """

    def __init__(self):
        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='Odgi', anchor='odgi',
                                            href='https://github.com/vgteam/odgi',
                                            info="is an optimized dynamic graph/genome implementation.")

        self.odgi_stats_map = dict()

        # Find and load any odgi stats file
        log_files = self.find_log_files('odgi/stats')
        if not log_files:
            raise UserWarning

        log.info("Found {} reports".format(len(self.odgi_stats_map)))

        # Parse odgi stats data
        for f in log_files:
            self.parse_odgi_stats_report(f)
            self.add_data_source(f)

        # Write parsed report data to a file
        self.write_data_file(self.odgi_stats_map, 'multiqc_odgi_stats')

        # Add the general section containing the general odgi stats
        self.plot_general_odgi_stats()

        # Plot the odgi stats metrics as a lineplot
        self.plot_odgi_metrics()

    def parse_odgi_stats_report(self, f):
        """
        The stats reports assume the following structure:
        
        length    nodes    edges    paths
        8778    168    243    35
        #mean_links_length
        path    in_node_space    in_nucleotide_space    num_links_considered
        all_paths    9.75053    497.321    942
        #sum_of_path_node_distances
        path    in_node_space    in_nucleotide_space    nodes    nucleotides    num_penalties    num_penalties_different_orientation
        all_paths    20.0686     19.5609    977     51365     90    0
        """
        lines = f['f'].splitlines()
        # parse the generals stats
        stats = lines[1].split('\t')
        # parse the mean links length
        mean_links_length = lines[4].split('\t')
        # parse sum of path nodes distances
        sum_of_path_nodes_distances = lines[7].split('\t')
        
        self.odgi_stats_map.update(MultiqcModule.compress_stats_data(f['fn'], stats, mean_links_length, sum_of_path_nodes_distances))

    def plot_general_odgi_stats(self):
        """
        Plot the odgi stats by adding them to the general statistics table.
        """
        data = dict()
        headers = OrderedDict()
        headers['Length'] = {
            'title': 'Length',
            'description': 'Graph length',
            'scale': 'BuPu'
        }
        headers['Nodes'] = {
            'title': 'Nodes',
            'description': 'Number of nodes in the graph',
            'scale': 'OrRd',
        }
        headers['Edges'] = {
            'title': 'Edges',
            'description': 'Number of edges in the graph',
            'scale': 'PuBu'
        }
        headers['Paths'] = {
            'title': 'Paths',
            'description': 'Number of paths through the graph',
            'scale': 'Greens'
        }
        for fn in self.odgi_stats_map.keys():
            file_stats = self.odgi_stats_map[fn]
            unique_file_identifier = MultiqcModule.strip_file_name(fn)
            data.update({unique_file_identifier: file_stats['General stats {}'.format(fn)]})
        self.general_stats_addcols(data, headers)

    def plot_odgi_metrics(self):
        """
        Plot odgi metrics as a lineplot supporting raw counts and log10 counts. 
        """
        mean_links_length_nodes_space = dict()
        mean_links_length_nucleotide_space = dict()
        sum_of_path_nodes_distances_nodes_space = dict()
        sum_of_path_nodes_distances_nucleotide_space = dict()
        odgi_stats_file_names = sorted(self.odgi_stats_map.keys())
        seq_smooth = odgi_stats_file_names[-2:]
        sorted_filenames = seq_smooth + odgi_stats_file_names[:-2]
        for fn in sorted_filenames:
            file_stats = self.odgi_stats_map[fn]
            unique_file_identifier = MultiqcModule.strip_file_name(fn)
            mean_links_length_nodes_space.update({unique_file_identifier: float(file_stats['Mean_links_length {}'.format(fn)]['In_node_space'])})
            mean_links_length_nucleotide_space.update({unique_file_identifier: float(file_stats['Mean_links_length {}'.format(fn)]['In_nucleotide_space'])})
            sum_of_path_nodes_distances_nodes_space.update(
                {unique_file_identifier: float(file_stats['Sum_of_path_nodes_distances {}'.format(fn)]['In_node_space'])})
            sum_of_path_nodes_distances_nucleotide_space.update(
                {unique_file_identifier: float(file_stats['Sum_of_path_nodes_distances {}'.format(fn)]['In_nucleotide_space'])})

        metrics_lineplot_config = {
            'categories': True,
            'yDecimals': False,
            'logswitch': True,
            'title': 'Odgi: Odgi metrics'
        }

        self.add_section(
            name='Odgi metrics',
            anchor='odgi-stats',
            description='The odgi metrics section',
            helptext='odgi metrics generated by the odgi stats module.',
            plot=linegraph.plot({'in_node_space_mean': mean_links_length_nodes_space,
                                 'in_nucleotide_space_mean': mean_links_length_nucleotide_space,
                                 'in_node_space_sum': sum_of_path_nodes_distances_nodes_space,
                                 'in_nucleotide_space_sum': sum_of_path_nodes_distances_nucleotide_space
                                 }, pconfig=metrics_lineplot_config)
        )

    @staticmethod
    def strip_file_name(fn):
        """
        Bla
        """
        if 'seqwish.og' in fn:
            return 'seqwish'
        elif 'smooth' in fn:
            return 'smooth'
        else:
            fn = fn.split('.')
            consensus_identifier = list((e for e in fn if 'consensus@' in e))
            try:
                return consensus_identifier[0]
            except IndexError:
                log.error('Unknown file name: File name must either contain seqwish, smooth or consensus@!')
                sys.exit(1)

    @staticmethod
    def compress_stats_data(fn, stats, mean_links_length, sum_of_path_nodes_distances) -> dict:
        """
        Compress odgi stats into a single dictionary
        """
        return {
            fn: {
                'General stats {}'.format(fn): {
                    'Length': float(stats[0]),
                    'Nodes': float(stats[1]),
                    'Edges': float(stats[2]),
                    'Paths': float(stats[3]),
                },
                'Mean_links_length {}'.format(fn): {
                    'Path': mean_links_length[0],
                    'In_node_space': mean_links_length[1],
                    'In_nucleotide_space': mean_links_length[2],
                    'Num_links_considered': mean_links_length[3]
                },
                'Sum_of_path_nodes_distances {}'.format(fn): {
                    'Path': sum_of_path_nodes_distances[0],
                    'In_node_space': sum_of_path_nodes_distances[1],
                    'In_nucleotide_space': sum_of_path_nodes_distances[2],
                    'Nodes': sum_of_path_nodes_distances[3],
                    'Nucleotides': sum_of_path_nodes_distances[4],
                    'Num_penalties': sum_of_path_nodes_distances[5],
                    'Num_penalties_different_orientation': sum_of_path_nodes_distances[6]
                }
            }
        }
