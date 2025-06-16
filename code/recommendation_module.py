# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 14:06:10 2015

@author: bitjoy.net
"""

from os import listdir
import xml.etree.ElementTree as ET
import os
import jieba
import jieba.analyse
import sqlite3
import configparser
from datetime import *
import math

import pandas as pd
import numpy as np

from sklearn.metrics import pairwise_distances

class RecommendationModule:
    stop_words = set()
    k_nearest = []
    
    config_path = ''
    config_encoding = ''
    
    doc_dir_path = ''
    doc_encoding = ''
    stop_words_path = ''
    stop_words_encoding = ''
    idf_path = ''
    db_path = ''
    
    def __init__(self, config_path, config_encoding):
        self.config_path = config_path
        self.config_encoding = config_encoding
        config = configparser.ConfigParser()
        config.read(config_path, config_encoding)
        
        self.doc_dir_path = config['DEFAULT']['doc_dir_path']
        self.doc_encoding = config['DEFAULT']['doc_encoding']
        self.stop_words_path = config['DEFAULT']['stop_words_path']
        self.stop_words_encoding = config['DEFAULT']['stop_words_encoding']
        self.idf_path = config['DEFAULT']['idf_path']
        self.db_path = config['DEFAULT']['db_path']

        f = open(self.stop_words_path, encoding = self.stop_words_encoding)
        words = f.read()
        self.stop_words = set(words.split('\n'))
    
    def write_k_nearest_matrix_to_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''DROP TABLE IF EXISTS knearest''')
        c.execute('''CREATE TABLE knearest
                     (id INTEGER PRIMARY KEY, first INTEGER, second INTEGER,
                     third INTEGER, fourth INTEGER, fifth INTEGER)''')

        for docid, doclist in self.k_nearest:
            c.execute("INSERT INTO knearest VALUES (?, ?, ?, ?, ?, ?)", tuple([docid] + doclist))

        conn.commit()
        conn.close()
    
    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False
            
    
    def construct_dt_matrix(self, files, topK = 200):
        jieba.analyse.set_stop_words(self.stop_words_path)
        jieba.analyse.set_idf_path(self.idf_path)
        M = len(files)
        N = 1
        terms = {}
        dt = []
        for i in files:
            root = ET.parse(self.doc_dir_path + i).getroot()
            title = root.find('title').text
            body = root.find('body').text
            docid = int(root.find('id').text)
            tags = jieba.analyse.extract_tags(title + '。' + body, topK=topK, withWeight=True)
            #tags = jieba.analyse.extract_tags(title, topK=topK, withWeight=True)
            cleaned_dict = {}
            for word, tfidf in tags:
                word = word.strip().lower()
                if word == '' or self.is_number(word):
                    continue
                cleaned_dict[word] = tfidf
                if word not in terms:
                    terms[word] = N
                    N += 1
            dt.append([docid, cleaned_dict])
        dt_matrix = [[0 for i in range(N)] for j in range(M)]
        i =0
        for docid, t_tfidf in dt:
            dt_matrix[i][0] = docid
            for term, tfidf in t_tfidf.items():
                dt_matrix[i][terms[term]] = tfidf
            i += 1

        dt_matrix = pd.DataFrame(dt_matrix)
        dt_matrix.index = dt_matrix[0]
        print('dt_matrix shape:(%d %d)'%(dt_matrix.shape))
        return dt_matrix
        
    def construct_k_nearest_matrix(self, similarity_matrix, k):
        # 假设 similarity_matrix 是 DataFrame，遍历每一行，找出每行最大的k个索引
        knearest = {}
        for i in similarity_matrix.index:
            # 取出当前行（Series），去掉自身（对角线）
            row = similarity_matrix.loc[i].copy()
            row[i] = -np.inf  # 排除自身
            # 取最大k个索引
            topk_idx = row.nlargest(k).index.tolist()
            knearest[i] = topk_idx
        self.k_nearest = [[int(key), value] for key, value in knearest.items()]
    
    def gen_idf_file(self):
        files = os.listdir(self.doc_dir_path)
        n = float(len(files))
        idf = {}
        for i in files:
            if not i.endswith('.xml'):
                continue
            xml_path = os.path.join(self.doc_dir_path, i)
            try:
                root = ET.parse(xml_path).getroot()
                title = root.find('title').text
                body = root.find('body').text
                seg_list = jieba.lcut(title + '。' + body, cut_all=False)
                seg_list = set(seg_list) - self.stop_words
                for word in seg_list:
                    word = word.strip().lower()
                    if word == '' or self.is_number(word):
                        continue
                    if word not in idf:
                        idf[word] = 1
                    else:
                        idf[word] = idf[word] + 1
            except ET.ParseError as e:
                print(f"[XML解析错误] 文件: {xml_path}，错误信息: {e}")
                continue
            except Exception as e:
                print(f"[其他错误] 文件: {xml_path}，错误信息: {e}")
                continue
        idf_file = open(self.idf_path, 'w', encoding = 'utf-8')
        for word, df in idf.items():
            idf_file.write('%s %.9f\n'%(word, math.log(n / df)))
        idf_file.close()
        
    def find_k_nearest(self, k, topK):
        self.gen_idf_file()
        files = listdir(self.doc_dir_path)
        dt_matrix = self.construct_dt_matrix(files, topK)
        self.construct_k_nearest_matrix(dt_matrix, k)
        self.write_k_nearest_matrix_to_db()
        
if __name__ == "__main__":
    print('-----start time: %s-----'%(datetime.today()))
    rm = RecommendationModule('../config.ini', 'utf-8')
    rm.find_k_nearest(5, 25)
    print('-----finish time: %s-----'%(datetime.today()))
    rm.find_k_nearest(5, 25)
    print('-----finish time: %s-----'%(datetime.today()))
