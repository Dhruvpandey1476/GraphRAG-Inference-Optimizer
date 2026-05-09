# Transformer Architecture and Large Language Models

## Introduction to Transformers

The Transformer architecture, introduced by Vaswani et al. in the landmark 2017 paper "Attention Is All You Need," revolutionized natural language processing. Unlike previous sequence-to-sequence models that relied on recurrent neural networks (RNNs) or long short-term memory networks (LSTMs), the Transformer relies entirely on attention mechanisms to draw global dependencies between input and output.

The core innovation of the Transformer is the self-attention mechanism, which allows each token in a sequence to attend to all other tokens simultaneously. This parallel processing capability makes Transformers dramatically faster to train than sequential RNN-based models and enables them to capture long-range dependencies in text that RNNs struggle with.

## Self-Attention Mechanism

Self-attention computes attention weights between every pair of tokens in a sequence using three learnable matrices: Query (Q), Key (K), and Value (V). The attention score between two tokens is computed as the dot product of their query and key vectors, scaled by the square root of the key dimension and passed through a softmax function. These scores determine how much each token attends to every other token when producing its contextual representation.

Multi-head attention extends this by running multiple attention operations in parallel across different subspaces of the representation. Each "head" learns different types of relationships — syntax, semantics, coreference, and so on. The outputs are concatenated and linearly projected to produce the final representation.

## BERT and Bidirectional Context

BERT (Bidirectional Encoder Representations from Transformers), developed by Google in 2018, applies the Transformer encoder to learn bidirectional contextual representations. BERT is pre-trained on two tasks: Masked Language Modeling (MLM), where random tokens are masked and the model must predict them using both left and right context, and Next Sentence Prediction (NSP), where the model predicts whether two sentences are consecutive in the original text.

This bidirectional pretraining gives BERT rich understanding of word meaning in context, making it highly effective for classification, question answering, and named entity recognition tasks. BERT and its variants (RoBERTa, DistilBERT, ALBERT) dominate NLP benchmark leaderboards for understanding tasks.

## GPT and Autoregressive Generation

GPT (Generative Pre-trained Transformer), developed by OpenAI, applies the Transformer decoder in an autoregressive fashion. GPT is pre-trained to predict the next token given all previous tokens, learning left-to-right causal context. This makes GPT and its successors (GPT-2, GPT-3, GPT-4) exceptionally good at text generation, dialogue, and instruction following.

GPT-3, released in 2020, demonstrated that scaling model size to 175 billion parameters dramatically improved few-shot and zero-shot task performance. GPT-4, released in 2023, introduced multimodal capabilities and significantly improved reasoning through training on more diverse data and RLHF alignment.

## Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation, introduced by Lewis et al. in 2020, combines parametric knowledge (stored in model weights) with non-parametric knowledge (retrieved from external documents). In a RAG pipeline, a query is used to retrieve relevant documents from an external knowledge base, which are then provided as context to the LLM for answer generation.

RAG significantly improves factual accuracy for domain-specific, recent, or long-tail knowledge that the base model may not have learned during pretraining. It also enables source attribution — the system can point to the specific documents used to generate an answer.

### Vector-Based RAG

Standard RAG uses dense vector embeddings to represent documents and queries. An embedding model (such as OpenAI's text-embedding-3-small or sentence-transformers) converts text into high-dimensional numerical vectors. Documents are indexed in a vector database (FAISS, Pinecone, Chroma, Weaviate) and queries are matched against documents using cosine similarity or inner product search.

The top-K most similar documents are retrieved and concatenated into a context window provided to the LLM. While effective for semantic matching, this approach has limitations: it retrieves documents based on surface similarity, not structural relationships, it cannot reason across multiple entities connected through different documents, and it scales token usage linearly with the number of retrieved chunks.

## Knowledge Graphs for AI

A knowledge graph organizes information as a directed graph of entities (nodes) and relationships (edges). Entities represent real-world objects — people, organizations, concepts, events, locations — while edges represent named relationships between them, such as "works_at," "founded_by," or "related_to."

Knowledge graphs enable multi-hop reasoning: starting from a seed entity, the system can traverse edges to discover related entities multiple hops away. This structural traversal can uncover connections that are difficult or impossible to find through keyword or vector similarity search alone.

## GraphRAG: Graph-Enhanced Retrieval

GraphRAG combines knowledge graph traversal with LLM generation. Instead of retrieving top-K text chunks, GraphRAG:

1. Extracts entities from the user query
2. Looks up those entities in a pre-built knowledge graph
3. Traverses the graph to find related entities and relationships (multi-hop)
4. Serializes the retrieved subgraph as structured context
5. Sends this compact, structured context to the LLM

The key advantage is token efficiency. A knowledge graph subgraph representing 50 entity-relationship pairs might require only 300-500 tokens, while the equivalent raw document chunks would require 3,000-5,000 tokens. This 6-10x compression directly reduces LLM API costs and latency.

## TigerGraph and GSQL

TigerGraph is a native parallel graph database designed for large-scale graph analytics. Its query language, GSQL, supports multi-hop traversals, pattern matching, accumulator-based aggregations, and distributed parallel computation across the graph.

TigerGraph Savanna is TigerGraph's managed cloud offering, providing fully hosted graph database clusters with REST API and Python SDK access. The TigerGraph GraphRAG repository provides a pre-built service layer for turning documents into knowledge graphs and exposing GraphRAG-powered Q&A APIs.

Key GSQL features for GraphRAG:
- SetAccum and ListAccum for collecting vertices and edges during traversal
- Multi-hop SELECT statements for n-hop neighborhood queries
- Parallel execution across the distributed graph
- Built-in shortest path and centrality algorithms

## Token Efficiency in Production AI

At production scale, token efficiency directly impacts cost, latency, and scalability. A system processing 1 million queries per day at 3,000 tokens each consumes 3 billion tokens daily. At GPT-4o-mini pricing (~$0.15 per million input tokens), that is $450 per day or $164,000 per year in input token costs alone.

A 70% token reduction brings this to $49,200 per year — a $114,800 annual saving from a single optimization. For larger enterprises using GPT-4 or Claude Opus, the savings scale proportionally higher.

Beyond cost, token reduction reduces end-to-end latency (fewer tokens to process = faster responses), increases effective throughput under rate limits, and reduces the risk of exceeding context window limits for complex multi-turn conversations.

## Evaluation Metrics for RAG Systems

### BERTScore
BERTScore computes the semantic similarity between generated and reference answers using contextual BERT embeddings. It computes precision (how much of the generated answer is in the reference), recall (how much of the reference is covered), and F1. A raw BERTScore F1 above 0.88 indicates strong semantic equivalence.

### LLM-as-a-Judge
LLM-as-a-Judge uses a capable LLM to evaluate generated answers on dimensions like correctness, completeness, relevance, and clarity. The judge model grades each answer independently or in comparison to a reference. A pass rate of 90%+ on LLM-as-a-Judge with scores ≥ 7/10 indicates production-quality answer generation.

### Faithfulness and Groundedness
Faithfulness measures whether generated claims are supported by the retrieved context. A faithful answer makes no claims beyond what the retrieved context supports. Groundedness ensures answers are based on retrieved facts rather than model hallucinations.
