import tensorflow as tf



class GATE():

    def __init__(self, hidden_dims, lambda_):
        self.lambda_ = lambda_
        self.n_layers = len(hidden_dims) -1
        self.W, self.v = self.define_weights(hidden_dims)
        self.C = {}


    def __call__(self, A, X, R, S):

        # Encoder
        H = X
        for layer in range(self.n_layers):
            H = self.__encoder(A, H, layer)

        # Final node representations
        self.H = H

        # Decoder
        for layer in range(self.n_layers - 1, -1, -1):
            H = self.__decoder(H, layer)
        X_ = H

        # The reconstruction loss of node features
        features_loss = tf.sqrt(tf.reduce_sum(input_tensor=tf.reduce_sum(input_tensor=tf.pow(X - X_, 2))))

        # The reconstruction loss of the graph structure
        self.S_emb = tf.nn.embedding_lookup(params=self.H, ids=S)
        self.R_emb = tf.nn.embedding_lookup(params=self.H, ids=R)
        structure_loss = -tf.math.log(tf.sigmoid(tf.reduce_sum(input_tensor=self.S_emb * self.R_emb, axis=-1)))
        structure_loss = tf.reduce_sum(input_tensor=structure_loss)

        # Total loss
        self.loss = features_loss + self.lambda_ * structure_loss

        return self.loss, self.H, self.C

    def __encoder(self, A, H, layer):
        H = tf.matmul(H, self.W[layer])
        self.C[layer] = self.graph_attention_layer(A, H, self.v[layer], layer)
        return tf.sparse.sparse_dense_matmul(self.C[layer], H)

    def __decoder(self, H, layer):
        H = tf.matmul(H, self.W[layer], transpose_b=True)
        return tf.sparse.sparse_dense_matmul(self.C[layer], H)

    def define_weights(self, hidden_dims):
        W = {}
        for i in range(self.n_layers):
            W[i] = tf.compat.v1.get_variable("W%s" % i, shape=(hidden_dims[i], hidden_dims[i+1]))

        Ws_att = {}
        for i in range(self.n_layers):
            v = {}
            v[0] = tf.compat.v1.get_variable("v%s_0" % i, shape=(hidden_dims[i+1], 1))
            v[1] = tf.compat.v1.get_variable("v%s_1" % i, shape=(hidden_dims[i+1], 1))
            Ws_att[i] = v

        return W, Ws_att

    def graph_attention_layer(self, A, M, v, layer):

        with tf.compat.v1.variable_scope("layer_%s"% layer):
            f1 = tf.matmul(M, v[0])
            f1 = A * f1
            f2 = tf.matmul(M, v[1])
            f2 = A * tf.transpose(a=f2, perm=[1, 0])
            logits = tf.sparse.add(a=f1, b=f2)

            unnormalized_attentions = tf.SparseTensor(indices=logits.indices,
                                         values=tf.nn.sigmoid(logits.values),
                                         dense_shape=logits.dense_shape)
            attentions = tf.sparse.softmax(unnormalized_attentions)

            attentions = tf.SparseTensor(indices=attentions.indices,
                                         values=attentions.values,
                                         dense_shape=attentions.dense_shape)

            return attentions