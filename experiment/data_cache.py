# -*- coding: utf-8 -*-
import h5py
from os import path
import textwrap2
import re


class dataCacheProxy():
    def __init__(self, file_path, stack_prefix='stack_'):
        """ filepath is for reading out files ONLY. To create new data files, please use the expInst interface """
        self.file_path = file_path
        self.current_stack = ''
        self.stack_prefix = stack_prefix

    def add(self, keyString, data):
        """method does not use chunked list, nor resizable."""
        def add_data(group, keyList, data):
            if len(keyList) == 1:
                try:
                    del group[keyList[0]]
                    group[keyList[0]] = np.array(data)
                except KeyError:
                    group[keyList[0]] = np.array(data)
                return
            else:
                try:
                    group.create_group(keyList[0])
                except ValueError:
                    pass
                return add_data(group[keyList[0]], keyList[1:], data)

        key_list = keyString.split('.')
        with h5py.File(self.file_path, 'a') as f:
            add_data(f, key_list, data)

    def append(self, key_string, data):
        def append_data(group, keyList, data):
            if not keyList:
                return
            data = np.array(data)
            if len(keyList) == 1:
                try:
                    # done: use reshape to make go faster
                    data_set = group[keyList[0]]
                    shape = list(data_set.shape)
                    shape[0] += 1
                    data_set.resize(shape)  # need to be chuncked dataset
                    data_set[-1] = data
                except KeyError:
                    shape = list(data.shape)
                    # note: dtype is important for string types 'S4' for 'blah' for example.
                    group.create_dataset(keyList[0], [1] + shape, maxshape=([None] + shape), chunks=True, dtype=data.dtype)
                    data_set = group[keyList[0]]
                    data_set[-1] = data
                return
            try:
                group.create_group(keyList[0])
            except ValueError:
                pass
            return append_data(group[keyList[0]], keyList[1:], data)

        keyList = key_string.split('.')
        with h5py.File(self.file_path, 'a') as f:
            append_data(f, keyList, data)

    def set(self, route, data):
        """
        add a datapoint to the current data stack.
        """
        try:
            if self.current_stack != '':
                if self.current_stack[-1] == '.': self.current_stack = self.current_stack[:-1]
                route = self.current_stack + "." + route
        except AttributeError:
            pass
        self.add(route, data)

    def post(self, route, data):
        """
        append a datapoint to the current data stack.
        """
        try:
            if self.current_stack != '':
                if self.current_stack[-1] == '.': self.current_stack = self.current_stack[:-1]
                route = self.current_stack + "." + route
        except AttributeError:
            pass
        self.append(route, data)

    def find(self, keyString):
        def get_data(f, keyList):
            if len(keyList) == 1:
                return f[keyList[0]][...];
            else:
                return get_data(f[keyList[0]], keyList[1:])

        keyList = keyString.split('.')
        with h5py.File(self.file_path, 'r') as f:
            return get_data(f, keyList)

    def get(self, route):
        """
        get a dataset from the current data stack.
        """
        try:
            if self.current_stack != '':
                if self.current_stack[-1] == '.': self.current_stack = self.current_stack[:-1]
                route = self.current_stack + '.' + route
        except AttributeError:
            pass
        return self.find(route)

    def get_next_stack_index(self):
        """ this also mutates the current_stack pointer, to point to the enxt stack
        """
        try:
            index = int(self.current_stack[-5:]) + 1
        except:
            index = 0
        self.current_stack = self.stack_prefix + str(100000 + index)[1:]
        return index

    def find_last_stack(self):
        try:
            index = int(self.current_stack[-5:])
        except AttributeError:
            index = 0
        except ValueError:
            index = 0
        while True:
            self.current_stack = self.stack_prefix + str(100000 + index)[1:]
            try:
                self.index()
                print "the last stack is ", self.current_stack
                break
            except IOError:
                print 'file does not exist, current_stack is ', self.current_stack;
                break
            except:
                index += 1
                print '.',

    def index(self, keyString=''):
        def get_indices(f, keyList):
            if len(keyList) == 0 or (keyList == ['', ]):
                try:
                    return f.keys()
                except AttributeError, e:
                    return e
            else:
                return get_indices(f[keyList[0]], keyList[1:])

        try:
            if keyString[-1] == '.':
                keyString = keyString[:-1]
        except IndexError, e:
            pass
        keyList = keyString.split('.')
        with h5py.File(self.file_path, 'r') as f:
            return get_indices(f, keyList)

    def index_current_stack(self, keyString=''):
        if self.current_stack == '':
            return self.index(keyString)
        else:
            return self.index(self.current_stack + '.' + keyString)

    def new_stack(self):
        index = self.get_next_stack_index()
        with h5py.File(self.file_path) as f:
            try:
                f.create_group(self.current_stack)
                print "new stack: ", self.current_stack;
            except ValueError, error:
                print "{} already exists. Move to next index.".format(self.current_stack)
                self.new_stack()

    def note(self, string, key_string=None, print_option=False, max_line_length=79):
        if not key_string:
            key_string = 'notes'
        if print_option:
            print key_string, string
        if max_line_length <= 0:
            self.post(key_string, string)
        else:
            for line in textwrap2.wrap(string, max_line_length):
                self.post(key_string, line + ' ' * (max_line_length - len(line)))

    def set_dict(self, keyString, d):
        """
        :param keyString:
        :param d:
        :return:
        """

        if not isinstance(d, dict):
            print 'object is not a dictionary object'
            return
        for key, value in d.iteritems():
            if isinstance(value, dict):
                self.set_dict(keyString + '.' + key, value)
            else:
                self.set(keyString + '.' + key, value)

    def get_dict(self, keyString):
        try:
            return self.get(keyString)
        except AttributeError:
            d = {}
            for key in self.index_current_stack(keyString):
                d[key] = self.get_dict(keyString + '.' + key)
            return d


import numpy as np
import time

if __name__ == "__main__":
    print "running a test..."

    # Setting up the instance
    cache = dataCacheProxy('./data_cache_test_file_01.h5')

    # test data
    test_data_x = np.arange(0, 10, 0.01)
    test_data_y = np.sin(test_data_x)

    cache.note("data_cache is awesome!", max_line_length=79)
    cache.note("the append option is O(k)!", max_line_length=79)

    # example usage
    cache.append('key1', (test_data_x, test_data_y))
    # plt.plot(cache.get('key1')[0][1])
    cache.append('key1', (test_data_x, test_data_y))

    cache.add('key2', (test_data_x, test_data_y))
    # plt.plot(cache.get('key2')[1])
    # plt.show()

    cache.add('group1.key1', (test_data_x, test_data_y))
    # plt.plot(cache.get('group1.key1')[1])
    cache.append('group1.key2', (test_data_x, test_data_y))
    # plt.plot(cache.get('group1.key2')[0][1])
    # plt.show()

    cache.add('group1.subgroup.key2', (test_data_x, test_data_y))
    # plt.plot(cache.get('group1.subgroup.key2')[1])
    cache.append('group1.subgroup.key3', (test_data_x, test_data_y))
    # plt.plot(cache.get('group1.subgroup.key3')[0][1])
    # plt.show()

    ### now test the set_dict method
    d = {
        'key0': 'haha',
        'key1': 'haha',
        'd0': {
            'key2': 'some stuff is here',
            'key3': 'some more stuff is here'
        }
    }
    ## new file then find the last stack
    cache = dataCacheProxy('./data_cache_test_file_02.h5')
    cache.find_last_stack()
    cache.set_dict('dictionary', d)
    print cache.index_current_stack('dictionary')
    d_copy = cache.get_dict('dictionary')
    print d, d_copy
    assert d == d_copy, 'set_dict and get_dict round-trip failed'

    cache.new_stack()
    for i in range(100):
        cache.append('test_array', [i])
    cache.new_stack()
    for i in range(100):
        cache.append('test_array', [i])

    ## create new file and just add to the root
    cache = dataCacheProxy('./data_cache_test_file_03.h5')
    cache.set_dict('dictionary', d)
    print cache.index_current_stack('dictionary')
    d_copy = cache.get_dict('dictionary')
    print d, d_copy
    assert d == d_copy, 'set_dict and get_dict round-trip failed'

    cache.find_last_stack()
    print 'the latest stack is: ', cache.current_stack

    # DataCache stack_index test
    cache = dataCacheProxy('./data_cache_test_file_04.h5')
    cache.new_stack()
    cache.post('mags', np.zeros(1601))
    cache.new_stack()
    cache.post('mags', np.zeros(1601))

    # DataCache Performance test
    print "starting performance measure"
    t0 = time.time()
    for i in range(200):
        print '.',
        cache.post('mags', np.zeros(1601))
    print "\ntime spent per iteration: {}s".format((time.time() - t0) / 200)
    t0 = time.time()
    for i in range(200):
        print '.',
        cache.post('mags', np.zeros(1601))
    print "\ntime spent per iteration: {}s".format((time.time() - t0) / 200)
    t0 = time.time()
    for i in range(200):
        print '.',
        cache.post('mags', np.zeros(1601))
    print "\ntime spent per iteration: {}s".format((time.time() - t0) / 200)
    t0 = time.time()
    for i in range(200):
        print '.',
        cache.post('mags', np.zeros(1601))
    print "\ntime spent per iteration: {}s".format((time.time() - t0) / 200)

    # now data is saved in the dataCache
    # now I want to move some data to a better file
    # each experiment is a file, contains:
    # - notes
    # - stack_<numeric>
    #   - configs
    #   - mags
    #   - fpts
    #   - vpts
