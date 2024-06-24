import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from vectorizers.transformers import InformationWeightTransformer
from vectorizers import NgramVectorizer

def cluster_avg_1D(cluster_data, y_data):
    #  Average out the y_data in each cluster,
    # to use as y-axis positions for the graph visualization
    clusters = np.unique(cluster_data)
    avg_arr = np.zeros(np.shape(clusters))
    i = 0
    for cluster in clusters:
        if cluster == -2:
            continue
        cl_idx = (cluster_data == cluster).nonzero()
        sum_ = 0
        for val in y_data[cl_idx]:
            sum_ += val
        sum_ /= np.size(cl_idx)
        avg_arr[i] = sum_
        i+=1

    return avg_arr

def cluster_most_common(cluster_data, y_data):
    # Get the most common y_data val in each cluster
    clusters = np.unique(cluster_data)
    most_arr = np.zeros(np.shape(clusters), dtype=int)
    i = 0

    for cluster in clusters:
        if cluster == -2:
            continue
        cl_idx = (cluster_data == cluster).nonzero()
        values, counts = np.unique(y_data[cl_idx], return_counts=True)
        most_ = values[np.argmax(counts)]
        most_arr[i] = int(most_)
        i += 1

    return most_arr

def graph_to_holoviews(G,dataset_func=None):
    nxNodes = G.nodes()
    nodes = nxNodes  # lol
    cnt = 0
    orphans = []
    idx = 0
    for node in nxNodes:
        if G.degree(node)==0:
            cnt+=1
            orphans.append(node)
            continue
        G.nodes()[node]['index'] = idx
        idx += 1

    for node in orphans:
        G.remove_node(node)
    nxNodes = G.nodes()
    if cnt != 0:
        print(f'Warning: removed {cnt} orphan nodes from the graph.')
    nodes_ = {"index": [], "size": [], "label": [], "colour": [], "column": []}
    for i, node in enumerate(nxNodes):
        nodes_["index"].append(i)
        nodes_["size"].append(nodes[node]['count'])
        try:
            nodes_["label"].append(nodes[node]['label'])
        except(KeyError):
            nodes_["label"].append(nodes[node]['index'])
        nodes_["colour"].append("#ffffff")
        nodes_["column"].append(nodes[node]['slice_no'])

    cmap = {nodes[node]['index']: nodes[node]['colour'] for node in nodes}
    try:
        nodes = hv.Dataset(nodes_, 'index', ['size', 'label', 'colour', 'column'])
    except(NameError):
        nodes = dataset_func(nodes_, 'index', ['size', 'label', 'colour','column'])

    edges = []

    for u, v, d in G.edges(data=True):
        uidx = nxNodes[u]['index']
        vidx = nxNodes[v]['index']
        u_size = nxNodes[u]['count']
        v_size = nxNodes[v]['count']
        edges.append((uidx, vidx, (u_size * d['src_weight'], v_size * d['dst_weight'])))

    return nodes, edges, cmap

def compute_cluster_yaxis(clusters, semantic_dist, func=cluster_avg_1D):
    y_data = []
    for tslice in clusters:
        y_datum = func(tslice, semantic_dist)
        y_data.append(y_datum)

    return y_data

def generate_keyword_labels(word_bags, TG, newline=True):
    ngram_vectorizer = NgramVectorizer()
    ngram_vectors = ngram_vectorizer.fit_transform(word_bags)
    ## Building cluster labels (crudely)
    IWT = InformationWeightTransformer()
    keywords = []
    for i in range(len(TG.slices)):
        # build a vector for each cluster by summing the vectors of its constituent data
        cluster_vectors = []
        for cl in np.unique(TG.clusters[i]):
            if (cl == -1) or (cl == -2):
                # skip outliers
                continue
            cl_idx = (TG.clusters[i] == cl).nonzero()
            vectors_in_cluster = ngram_vectors[cl_idx]
            cl_vector = np.sum(vectors_in_cluster,axis=0)
            cluster_vectors.append(cl_vector)
        print("IWT on slice:",i,end="\r")    
            
        # IWT the vectors and get the most important keywords
        cluster_vectors = np.squeeze(np.array(cluster_vectors))
        weighted_vectors = IWT.fit_transform(cluster_vectors)
        cluster_keywords = []
        for cl_vector in weighted_vectors:
            cl_vector = np.squeeze(cl_vector)
            first_, second_, third_ = np.argsort(cl_vector)[-3:]
            w1 = ngram_vectorizer._inverse_token_dictionary_[first_]
            w2 = ngram_vectorizer._inverse_token_dictionary_[second_]
            w3 = ngram_vectorizer._inverse_token_dictionary_[third_]
            row = np.array([w1,w2,w3])
            cluster_keywords.append(row)
        keywords.append(cluster_keywords)
        t_attrs = nx.get_node_attributes(TG.G, 'slice_no')
    cl_attrs = nx.get_node_attributes(TG.G, 'cluster_no')
    label_attrs = {}
    for node in TG.G.nodes():
        t_idx = t_attrs[node]
        cl_idx = cl_attrs[node]
        words = keywords[t_idx][cl_idx]
        if newline:
            label_attrs[node] = words[0]+'\n'+words[1]+'\n'+words[2] 
        else:
            label_attrs[node] = words[0]+' '+words[1]+' '+words[2] 
    
    nx.set_node_attributes(TG.G, label_attrs, 'label')
    return TG
