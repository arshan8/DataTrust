# The LLM GPT Pipeline

This document explains the step-by-step pipeline of a Transformer-based Large Language Model (like GPT) during a forward pass (inference) and training.

---

## 1. Tokenization

The input text is first broken down into sub-word units called **tokens**.

* **Input Text**: `"I love cats"`
* **Tokenizer Output**: `["I", " love", " cats"]`

Each token in the vocabulary is mapped to a unique, deterministic integer ID. These IDs contain no semantic meaning themselves; they are simply indices.

* **Example Mapping**:
  * `"I"` $\rightarrow$ `40`
  * `" love"` $\rightarrow$ `1842`
  * `" cats"` $\rightarrow$ `9123`

---

## 2. Embedding Lookup

Using the token ID, the model retrieves a dense vector of floating-point numbers representing that token from a static lookup table.

```
Token ID: 40 ──► [ Embedding Matrix Lookup ] ──► [ 0.53, -0.12, ... ]
```

This is a direct index-lookup operation, equivalent to:
```python
embedding = embedding_matrix[token_id]
```

An **embedding** is a vector in high-dimensional space. Words with similar meanings or grammatical roles are mapped to vectors that sit close to each other in this coordinate space.

---

## 3. Static vs. Contextual Embeddings

### **Initial Embeddings Have No Context**
The lookup embedding for a word is always identical.
* E.g., the word **"bank"** gets the exact same initial vector in both of these sentences:
  1. *"I deposited money in the bank."*
  2. *"The river bank is beautiful."*

At this stage, context has not yet been integrated.

---

## 4. The Self-Attention Mechanism (Q, K, V)

The static embeddings are not used directly to calculate attention. Instead, the model transforms each embedding ($E$) using learned weight projection matrices to create three vectors:

* **Query ($Q$)**: Represents what the current token is looking for ($Q = E \times W^Q$).
* **Key ($K$)**: Represents what information the current token contains ($K = E \times W^K$).
* **Value ($V$)**: Represents the actual content payload of the token ($V = E \times W^V$).

### **How Attention Works**
Each token computes its relation to other tokens in the sequence:
1. The model compares the **Query** of the target word with the **Keys** of all other words in the sentence.
2. This calculation yields **attention weights** (representing how important each word is to the current word).
3. The model multiplies these weights by the corresponding **Value** vectors to get a weighted sum.

* **Example**: In *"I deposited money in the bank"*, the token **"bank"** will attend strongly to the keys of **"money"** and **"deposited"**. The blended values result in a new representation of `"bank"` that encodes its financial context.

---

## 5. Contextual Embeddings & Layers

Through attention, the model shifts from static to contextual representations:
* **Lookup Embedding**: Re-read from the static table; remains fixed during the forward pass.
* **Contextual Embedding (Hidden State)**: The vector *after* the attention calculation, containing context from surrounding words.

### **Multiple Transformer Layers**
This process is repeated across multiple stacked layers in the transformer:
```
Current Embeddings ──► Project Q, K, V ──► Calculate Attention ──► Richer Contextual Embeddings
```
As the representation passes through each layer, the contextual embeddings capture increasingly abstract relationships.
* **Layer 1**: `"bank"` gets basic financial context.
* **Layer 6**: `"bank"` is represented as a financial institution specifically used in this exact transaction sentence.

---

## 6. Sentence Representation in Decoder LLMs (GPT)
GPT-style autoregressive decoders **do not create a single sentence embedding** to generate text. Instead, the model maintains and calculates one active contextual vector (hidden state) **per token**:
* `"I"` $\rightarrow$ Contextual Vector
* `" love"` $\rightarrow$ Contextual Vector
* `" cats"` $\rightarrow$ Contextual Vector

---

## 7. Inference vs. Training

### **Inference (Running the Model)**
When you generate text (e.g. asking *"Why is the sky blue?"*):
1. **Flow**: `Text` $\rightarrow$ `Tokenizer` $\rightarrow$ `Token IDs` $\rightarrow$ `Embedding Lookup` $\rightarrow$ `Transformer Layers` $\rightarrow$ `Predict Next Token`.
2. **Read-Only**: The model parameters (weights) are static and **do not change**.

### **Training (Learning the Model)**
During training, the model does the same forward pass but then compares its prediction against the target answer to compute the **loss (error)**.

1. **Loss Computation**: E.g., the model predicted *"The cat barked"* instead of *"The cat meowed"*.
2. **Backpropagation**: The loss is propagated backward through the network to compute gradients.
3. **Weight Updates**: The gradients are used to update the weights of:
   * The **Embedding Matrix**
   * The **Attention projection matrices** ($W^Q$, $W^K$, $W^V$)
   * The **Feed-forward networks** and output classification layers
