import os
import sys
import math
import random
import argparse
import operator
import pdb
import xml4h
import spacy
import torch
import torch.autograd as autograd
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from torch.utils.data import Dataset, DataLoader

from collections import defaultdict
from collections import Counter
from torch.autograd import Variable


class TextLoader:
  def __init__(self, data_dir, test_dir):

    self.token2id = defaultdict(int)
    # prepare data
    self.token_set, train_data, test_data = self.load_data(data_dir, test_dir)

    # split data
    self.train_data, self.dev_data, self.test_data = self.split_data(train_data, test_data)

    # token and category vocabulary
    self.token2id = self.set2id(self.token_set, 'PAD', 'UNK')
    self.tag2id = self.set2id(set((train_data).keys()))

  def load_data(self, data_dir, test_dir):
    tok = spacy.load('en')
    train_files, test_files = [], []
    token_set = set()
    train_data, test_data = defaultdict(list), defaultdict(list)
    for path, dirnames, filenames in os.walk(data_dir):
      # print('{} {} {}'.format(repr(path), repr(dirnames), repr(filenames)))
      for file in filenames:
        if os.path.splitext(file)[1] == '.xml':
          file_path = path + "/" + file
          train_files.append(file_path)

    for path, dirnames, filenames in os.walk(test_dir):
      # print('{} {} {}'.format(repr(path), repr(dirnames), repr(filenames)))
      for file in filenames:
        if os.path.splitext(file)[1] == '.xml':
          file_path = path + "/" + file
          test_files.append(file_path)

    for file in train_files:
      print(file)
      doc = xml4h.parse(file)
      for st_ans in doc.question.studentAnswers.studentAnswer:
        #print(st_ans.text)
        cat = st_ans["accuracy"]
        line = [token.text for token in tok.tokenizer(st_ans.text)]
        train_data[cat].append(line)
        for token in line:
          token_set.add(token)

    for file in test_files:
      print(file)
      doc = xml4h.parse(file)
      for st_ans in doc.question.studentAnswers.studentAnswer:
        #print(st_ans.text)
        cat = st_ans["accuracy"]
        line = [token.text for token in tok.tokenizer(st_ans.text)]
        test_data[cat].append(line)
        # for token in line:
        #   token_set.add(token)

    return token_set, train_data, test_data


  def split_data(self, train_data, test_data):
    """
    Split data into train, dev, and test (currently use 80%/10%/10%)
    It is more make sense to split based on category, but currently it hurts performance
    """
    train_split = []
    dev_split = []

    print('Data statistics: ')

    all_data = []
    test = []
    for cat in train_data:
      cat_data = train_data[cat]
      print(cat, len(train_data[cat]))
      all_data += [(dat, cat) for dat in cat_data]

    for cat in test_data:
      cat_data = test_data[cat]
      print(cat, len(test_data[cat]))
      test += [(dat, cat) for dat in cat_data]

    all_data = random.sample(all_data, len(all_data))

    train_ratio = int(len(all_data) * 0.9)
    dev_ratio = int(len(all_data) * 1.0)

    train_split = all_data[:train_ratio]
    dev_split = all_data[train_ratio:dev_ratio]

    train_cat = set()
    for item, cat in train_split:
      train_cat.add(cat)
    print('Train categories:', sorted(list(train_cat)))

    dev_cat = set()
    for item, cat in dev_split:
      dev_cat.add(cat)
    print('Dev categories:', sorted(list(dev_cat)))

    test_cat = set()
    for item, cat in test:
      test_cat.add(cat)
    print('Test categories:', sorted(list(test_cat)))
    #assert 1 == 0
    return train_split, dev_split, test


  def set2id(self, item_set, pad=None, unk=None):
    item2id = defaultdict(int)
    if pad is not None:
      item2id[pad] = 0
    if unk is not None:
      item2id[unk] = 1

    for item in item_set:
      item2id[item] = len(item2id)

    return item2id


"""
We are going to use the Dataset interface provided
by pytorch wich is really convenient when it comes to
batching our data
"""
class PaddedTensorDataset(Dataset):
    """Dataset wrapping data, target and length tensors.
    Each sample will be retrieved by indexing both tensors along the first
    dimension.
    Arguments:
        data_tensor (Tensor): contains sample data.
        target_tensor (Tensor): contains sample targets (labels).
        length (Tensor): contains sample lengths.
        raw_data (Any): The data that has been transformed into tensor, useful for debugging
    """

    def __init__(self, data_tensor, target_tensor, length_tensor, raw_data):
        assert data_tensor.size(0) == target_tensor.size(0) == length_tensor.size(0)
        self.data_tensor = data_tensor
        # print("=========================")
        # print(data_tensor)

        self.target_tensor = target_tensor
        self.length_tensor = length_tensor
        self.raw_data = raw_data


    def __getitem__(self, index):
        return self.data_tensor[index], self.target_tensor[index], self.length_tensor[index], self.raw_data[index]

    def __len__(self):
        return self.data_tensor.size(0)