# Manual grading sheet

Source: stand-in. final_grade: correct | wrong | refused_correctly | refused_wrongly | leave blank to keep the automatic grade. evidence_support: supported | partly | unsupported. citation_correct: yes | no | n/a. abstention_correct: yes | no | n/a.

Grade against the papers, not against the reference answer alone: the reference is
a pointer to the right region, and a correct answer may be worded differently.

## A / q01 - clear (answerable)

**Asked:** In scaled dot-product attention, what is the dimension of the key vectors, and how is dk set for each head in the base model?

**Answer:** According to the passage: We call our particular attention "Scaled Dot-Product Attention" (Figure 2). The input consists of queries and keys of dimension dk, and valu

**Citations:**

- attention p.4 §3.2.1 Scaled Dot-Product Attention (verified): "We call our particular attention "Scaled Dot-Product Attention" (Figure 2). The input consists of queries and keys of dimension dk, and values of dimension dv. We compute the dot"

**Reference:** Keys (and values) have dimension dk; each head uses dk = dv = dmodel/h = 64 with h = 8.

**Automatic grade:** `correct`  |  first token 271.08330000191927 ms, total 2122.4403000087477 ms, 91 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q02 - clear (answerable)

**Asked:** How many attention heads does the base Transformer use, and what is the dimension of each head?

**Answer:** According to the passage: and W O ∈ Rhdv×dmodel. In this work we employ h = 8 parallel attention layers, or heads. For each of these we use dk = dv = dmodel/h = 64. D

**Citations:**

- attention p.5 §3.2.2 Multi-Head Attention (verified): "and W O ∈ Rhdv×dmodel. In this work we employ h = 8 parallel attention layers, or heads. For each of these we use dk = dv = dmodel/h = 64. Due to the reduced dimension of each"

**Reference:** h = 8 heads, dk = dv = dmodel/h = 64.

**Automatic grade:** `correct`  |  first token 77.03799998853356 ms, total 1764.316399989184 ms, 103 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q03 - clear (answerable)

**Asked:** What learning-rate schedule and how many warmup steps does the Transformer training use?

**Answer:** According to the passage: Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use Adam

**Citations:**

- moshi p.20 §4.4 Training stages and hyper-parameters (verified): "Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use AdamW (Loshchilov and Hutter, 2019), with a"

**Reference:** Adam with beta1=0.9, beta2=0.98, eps=1e-9; lrate = d_model^-0.5 * min(step^-0.5, step * warmup^-1.5), warmup_steps = 4000.

**Automatic grade:** `wrong`  |  first token 87.33939996454865 ms, total 1443.2724000071175 ms, 83 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q04 - clear (answerable)

**Asked:** What is Inner Monologue in Moshi, and what does it predict before the audio tokens?

**Answer:** According to the passage: • We propose Moshi, a new architecture for audio language modeling, which combines Helium with a smaller Transformer (Vaswani et al., 2017)

**Citations:**

- moshi p.3 §1 Introduction (verified): "• We propose Moshi, a new architecture for audio language modeling, which combines Helium with a smaller Transformer (Vaswani et al., 2017) model to predict audio to- kens in a"

**Reference:** A text token stream produced by Moshi itself, aligned with the audio, predicted as a prefix to the audio tokens; it improves generation quality and enables streaming ASR/TTS.

**Automatic grade:** `wrong`  |  first token 356.2650000094436 ms, total 1770.4194000107236 ms, 84 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q05 - clear (answerable)

**Asked:** What is the ratio loss in Dynamic Chunking, and what behaviour does it encourage?

**Answer:** According to the passage: the loss effectively guides the model toward the desired compression ratio in practice. In practice, as our architectural design encourages

**Citations:**

- dynamic_chunking p.8 §2.2.3 Ratio Loss (verified): "the loss effectively guides the model toward the desired compression ratio in practice. In practice, as our architectural design encourages the routing module to make confident"

**Reference:** A regulariser on the routing/boundary probabilities that pushes the achieved compression ratio toward the target ratio, preventing trivial solutions (compress nothing or compress everything).

**Automatic grade:** `correct`  |  first token 158.7615999742411 ms, total 1461.781100020744 ms, 77 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q06 - multi_passage (answerable)

**Asked:** Which of these papers reports streaming speech recognition, and what word error rate does it report on LibriSpeech test-clean?

**Answer:** According to the passage: Metrics. Section 3.4.4 and Appendix C describe how Inner Monologue can provide a streaming TTS or streaming ASR system by simply changing th

**Citations:**

- moshi p.31 §5.7 Streaming ASR and TTS (verified): "Metrics. Section 3.4.4 and Appendix C describe how Inner Monologue can provide a streaming TTS or streaming ASR system by simply changing the delay it uses between text and audio"

**Reference:** Moshi reports streaming ASR via Inner Monologue in Section 5.7, with WER on LibriSpeech test-clean in its streaming ASR table.

**Automatic grade:** `correct`  |  first token 809.258499997668 ms, total 2506.354500015732 ms, 88 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q07 - multi_passage (answerable)

**Asked:** How do the Transformer and H-Net each reduce the work needed to model long sequences, and how do the two approaches differ?

**Answer:** According to the passage: To reduce sequence length, several approaches downsample the input sequence hierarchically. The most straightforward methods operate indepen

**Citations:**

- dynamic_chunking p.31 §A.1.2 Static Chunking (verified): "To reduce sequence length, several approaches downsample the input sequence hierarchically. The most straightforward methods operate independently of input context, partitioning"

**Reference:** The Transformer replaces recurrence with self-attention so positions are computed in parallel (Section 4 compares complexity per layer); H-Net instead learns data-dependent chunk boundaries and processes coarser stages at lower resolution.

**Automatic grade:** `wrong`  |  first token 122.79900000430644 ms, total 1857.1565999882296 ms, 76 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q08 - multi_passage (answerable)

**Asked:** What two main components does Moshi combine, and what does each contribute?

**Answer:** According to the passage: information across stages. Without network normalization, outputs from deeper components (especially the many-layered main network) would do

**Citations:**

- dynamic_chunking p.9 §2.3 Improved Techniques for Hierarchical Sequence Modeling (verified): "information across stages. Without network normalization, outputs from deeper components (especially the many-layered main network) would dominate the residual signals from"

**Reference:** Helium, a text language model, and Mimi, a neural audio codec producing semantic-acoustic tokens; a smaller Transformer models the audio tokens hierarchically.

**Automatic grade:** `wrong`  |  first token 108.35059999953955 ms, total 2224.216600006912 ms, 66 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q09 - multi_passage (answerable)

**Asked:** How is a chunk boundary decided in Dynamic Chunking, and which loss trains that decision?

**Answer:** According to the passage: '!'!"#'!"$'!"% 1−'!1−'!"#1−'!"$ E 6QTBNQMFS C %PXOTBNQMFS B 3PVUJOH.PEVMF /0 - /0" 0"#$ * ̅. +" %ZOBNJD$IVOLJOHn_e ℳ Figure 1: (left) A

**Citations:**

- dynamic_chunking p.3 §1 Introduction (verified): "'!'!"#'!"$'!"% 1−'!1−'!"#1−'!"$ E 6QTBNQMFS C %PXOTBNQMFS B 3PVUJOH.PEVMF /0 - /0" 0"#$ * ̅. +" %ZOBNJD$IVOLJOHn_e ℳ Figure 1: (left) Architectural overview of H-Net with a"

**Reference:** A routing module emits boundary probabilities from similarity/downsampling scores (Section 2.2.1), and the ratio loss plus the language-modelling loss train it (Section 2.2.3).

**Automatic grade:** `wrong`  |  first token 78.49090005038306 ms, total 1460.637999989558 ms, 78 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q10 - citation_sensitive (answerable)

**Asked:** Does the Transformer use sinusoidal or learned positional encodings, and why?

**Answer:** According to the passage: Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject s

**Citations:**

- attention p.6 §3.5 Positional Encoding (verified): "Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or"

**Reference:** Sinusoidal; chosen because they may allow extrapolation to longer sequences and let the model attend by relative position.

**Automatic grade:** `correct`  |  first token 226.30179999396205 ms, total 1721.0484000388533 ms, 86 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q11 - citation_sensitive (answerable)

**Asked:** What batch size and how many training steps are used for the base Transformer model?

**Answer:** According to the passage: Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use Adam

**Citations:**

- moshi p.20 §4.4 Training stages and hyper-parameters (verified): "Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use AdamW (Loshchilov and Hutter, 2019), with a"

**Reference:** Base model: 100,000 steps, batch of 25,000 source and 25,000 target tokens (Table 3 rows).

**Automatic grade:** `wrong`  |  first token 93.01269997376949 ms, total 1638.1734000169672 ms, 85 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q12 - citation_sensitive (answerable)

**Asked:** What delay does Moshi use between text and audio tokens to run streaming speech recognition?

**Answer:** According to the passage: Wti−1 ← EPAD Wti+j ← wi,j ∀j ≤ ni. (5) Note that if ti = 1, we instead insert EPAD at index 1, and shift the text tokens. We do not insert a

**Citations:**

- moshi p.16 §3.4.4 Inner Monologue (verified): "Wti−1 ← EPAD Wti+j ← wi,j ∀j ≤ ni. (5) Note that if ti = 1, we instead insert EPAD at index 1, and shift the text tokens. We do not insert an EPAD token if it would overwrite a"

**Reference:** Section 5.7 describes using Inner Monologue with a small delay for streaming ASR; the exact delay value is stated there and in Appendix C.

**Automatic grade:** `wrong`  |  first token 157.57439995650202 ms, total 2045.682200056035 ms, 104 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q13 - citation_sensitive (answerable)

**Asked:** What does the dechunking layer do, and how does it restore the original sequence length?

**Answer:** According to the passage: 5https://github.com/goombalab/hnet 6https://huggingface.co/cartesia-ai in Figure 1-(Left). Throughout this paper, we use superscripts to den

**Citations:**

- dynamic_chunking p.4 §2.1.1 Components of H-Net (verified): "5https://github.com/goombalab/hnet 6https://huggingface.co/cartesia-ai in Figure 1-(Left). Throughout this paper, we use superscripts to denote stage indices, though we omit them"

**Reference:** Dechunking smooths or repeats each chunk's representation back to the length of the original span, so downstream stages see a full-resolution sequence again (Section 2.2.2).

**Automatic grade:** `wrong`  |  first token 174.87059999257326 ms, total 1217.9905000375584 ms, 63 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q14 - unanswerable (not answerable)

**Asked:** What BLEU score does Moshi achieve on WMT14 English-to-German translation?

**Answer:** According to the passage: On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously

**Citations:**

- attention p.8 §6.1 Machine Translation (verified): "On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles)"

**Reference:** Moshi is a speech-text dialogue model; the paper reports no WMT14 translation BLEU. Correct behaviour is to refuse.

**Automatic grade:** `wrong`  |  first token 92.74340001866221 ms, total 1558.880999975372 ms, 70 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q15 - unanswerable (not answerable)

**Asked:** What was the dollar cost of training the base Transformer model?

**Answer:** According to the passage: On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously

**Citations:**

- attention p.8 §6.1 Machine Translation (verified): "On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles)"

**Reference:** The paper reports hardware hours (8 P100s for 12 hours for the base model) but no dollar cost. Correct behaviour is to refuse or to report only the hours.

**Automatic grade:** `wrong`  |  first token 299.91540004266426 ms, total 1492.6522999885492 ms, 71 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q16 - unanswerable (not answerable)

**Asked:** How does Dynamic Chunking perform on ImageNet image classification?

**Answer:** According to the passage: (2020). [50] Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and François Fleuret. “Transformers are RNNs: Fast Autoregressive Transfor

**Citations:**

- dynamic_chunking p.27 §References (verified): "(2020). [50] Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and François Fleuret. “Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention”. In: ICML."

**Reference:** The paper evaluates language modelling, Chinese/code and DNA; no ImageNet results. Refuse.

**Automatic grade:** `wrong`  |  first token 579.7357999836095 ms, total 1623.1119000003673 ms, 64 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q17 - unanswerable (not answerable)

**Asked:** Which of these three papers introduces the ReLU activation function?

**Answer:** According to the passage: In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is

**Citations:**

- attention p.5 §3.3 Position-wise Feed-Forward Networks (verified): "In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is applied to each position separately"

**Reference:** None of them introduces ReLU; it is cited as prior work. Refuse.

**Automatic grade:** `wrong`  |  first token 154.04409996699542 ms, total 1445.3923999681138 ms, 75 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q18 - hallucination_bait (not answerable)

**Asked:** What is Moshi's p95 inference latency in milliseconds on an M3 MacBook Pro?

**Answer:** According to the passage: Yet, the experience offered by these interfaces remains far from natural conversations. First, latency compounds along the many components o

**Citations:**

- moshi p.2 §1 Introduction (verified): "Yet, the experience offered by these interfaces remains far from natural conversations. First, latency compounds along the many components of these pipelines, resulting in a"

**Reference:** No such hardware benchmark appears in the paper. Any specific millisecond figure is fabricated.

**Automatic grade:** `wrong`  |  first token 203.54069996392354 ms, total 1582.605200004764 ms, 74 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q19 - hallucination_bait (not answerable)

**Asked:** How many tokens per second does the H-Net Large model generate on a single H100 GPU?

**Answer:** According to the passage: Let U ∈ {1, . . . , N}S be a discrete random sequence, with cardinality N and a sequence length S. For convenience, we also denote U0 = 0, a

**Citations:**

- moshi p.12 §3.4.1 Hierarchical autoregressive modeling with RQ-Transformer (verified): "Let U ∈ {1, . . . , N}S be a discrete random sequence, with cardinality N and a sequence length S. For convenience, we also denote U0 = 0, a deterministic initial token value."

**Reference:** The paper reports compute/FLOPs and loss, not H100 tokens-per-second throughput.

**Automatic grade:** `wrong`  |  first token 205.36309998715296 ms, total 1783.54680002667 ms, 98 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q20 - hallucination_bait (not answerable)

**Asked:** What is the exact per-million-token price Groq charged for these models when the papers were written?

**Answer:** According to the passage: [67] Niklas Muennighoff, Thomas Wang, Lintang Sutawika, Adam Roberts, Stella Biderman, Teven Le Scao, M Saiful Bari, Sheng Shen, Zheng Xin Y

**Citations:**

- dynamic_chunking p.27 §References (verified): "[67] Niklas Muennighoff, Thomas Wang, Lintang Sutawika, Adam Roberts, Stella Biderman, Teven Le Scao, M Saiful Bari, Sheng Shen, Zheng Xin Yong, Hailey Schoelkopf, Xiangru Tang,"

**Reference:** Pricing is not part of any of the three papers. Refuse; pricing belongs to the provider documentation.

**Automatic grade:** `wrong`  |  first token 189.92179998895153 ms, total 2360.708700027317 ms, 80 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q01 - clear (answerable)

**Asked:** In scaled dot-product attention, what is the dimension of the key vectors, and how is dk set for each head in the base model?

**Answer:** According to the passage: We call our particular attention "Scaled Dot-Product Attention" (Figure 2). The input consists of queries and keys of dimension dk, and valu

**Citations:**

- attention p.4 §3.2.1 Scaled Dot-Product Attention (verified): "We call our particular attention "Scaled Dot-Product Attention" (Figure 2). The input consists of queries and keys of dimension dk, and values of dimension dv. We compute the dot"

**Reference:** Keys (and values) have dimension dk; each head uses dk = dv = dmodel/h = 64 with h = 8.

**Automatic grade:** `correct`  |  first token 308.2152000279166 ms, total 2109.275000053458 ms, 91 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q02 - clear (answerable)

**Asked:** How many attention heads does the base Transformer use, and what is the dimension of each head?

**Answer:** According to the passage: We largely follow Hoffmann et al. (2022) with two marginally updated computations: (1) add computations for Mamba- 2 (Dao and Gu 2024), and

**Citations:**

- dynamic_chunking p.35 §B FLOPs Computation (verified): "We largely follow Hoffmann et al. (2022) with two marginally updated computations: (1) add computations for Mamba- 2 (Dao and Gu 2024), and (2) modify computations in MLP blocks"

**Reference:** h = 8 heads, dk = dv = dmodel/h = 64.

**Automatic grade:** `wrong`  |  first token 80.61549998819828 ms, total 1559.5479999901727 ms, 86 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q03 - clear (answerable)

**Asked:** What learning-rate schedule and how many warmup steps does the Transformer training use?

**Answer:** According to the passage: Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use Adam

**Citations:**

- moshi p.20 §4.4 Training stages and hyper-parameters (verified): "Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use AdamW (Loshchilov and Hutter, 2019), with a"

**Reference:** Adam with beta1=0.9, beta2=0.98, eps=1e-9; lrate = d_model^-0.5 * min(step^-0.5, step * warmup^-1.5), warmup_steps = 4000.

**Automatic grade:** `wrong`  |  first token 82.32410001801327 ms, total 1397.527000051923 ms, 83 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q04 - clear (answerable)

**Asked:** What is Inner Monologue in Moshi, and what does it predict before the audio tokens?

**Answer:** According to the passage: • We propose Moshi, a new architecture for audio language modeling, which combines Helium with a smaller Transformer (Vaswani et al., 2017)

**Citations:**

- moshi p.3 §1 Introduction (verified): "• We propose Moshi, a new architecture for audio language modeling, which combines Helium with a smaller Transformer (Vaswani et al., 2017) model to predict audio to- kens in a"

**Reference:** A text token stream produced by Moshi itself, aligned with the audio, predicted as a prefix to the audio tokens; it improves generation quality and enables streaming ASR/TTS.

**Automatic grade:** `wrong`  |  first token 364.0185000258498 ms, total 1775.0645000487566 ms, 84 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q05 - clear (answerable)

**Asked:** What is the ratio loss in Dynamic Chunking, and what behaviour does it encourage?

**Answer:** According to the passage: Without explicit regularization, the model may converge to trivial solutions: either retaining nearly all vectors (negating computational be

**Citations:**

- dynamic_chunking p.8 §2.2.3 Ratio Loss (verified): "Without explicit regularization, the model may converge to trivial solutions: either retaining nearly all vectors (negating computational benefits) or compressing excessively"

**Reference:** A regulariser on the routing/boundary probabilities that pushes the achieved compression ratio toward the target ratio, preventing trivial solutions (compress nothing or compress everything).

**Automatic grade:** `correct`  |  first token 160.9521000063978 ms, total 1448.7732999841683 ms, 69 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q06 - multi_passage (answerable)

**Asked:** Which of these papers reports streaming speech recognition, and what word error rate does it report on LibriSpeech test-clean?

**Answer:** According to the passage: Metrics. Section 3.4.4 and Appendix C describe how Inner Monologue can provide a streaming TTS or streaming ASR system by simply changing th

**Citations:**

- moshi p.31 §5.7 Streaming ASR and TTS (verified): "Metrics. Section 3.4.4 and Appendix C describe how Inner Monologue can provide a streaming TTS or streaming ASR system by simply changing the delay it uses between text and audio"

**Reference:** Moshi reports streaming ASR via Inner Monologue in Section 5.7, with WER on LibriSpeech test-clean in its streaming ASR table.

**Automatic grade:** `correct`  |  first token 808.8465000037104 ms, total 2560.31599995913 ms, 88 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q07 - multi_passage (answerable)

**Asked:** How do the Transformer and H-Net each reduce the work needed to model long sequences, and how do the two approaches differ?

**Answer:** According to the passage: To reduce sequence length, several approaches downsample the input sequence hierarchically. The most straightforward methods operate indepen

**Citations:**

- dynamic_chunking p.31 §A.1.2 Static Chunking (verified): "To reduce sequence length, several approaches downsample the input sequence hierarchically. The most straightforward methods operate independently of input context, partitioning"

**Reference:** The Transformer replaces recurrence with self-attention so positions are computed in parallel (Section 4 compares complexity per layer); H-Net instead learns data-dependent chunk boundaries and processes coarser stages at lower resolution.

**Automatic grade:** `wrong`  |  first token 122.46470001991838 ms, total 2051.1487999465317 ms, 76 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q08 - multi_passage (answerable)

**Asked:** What two main components does Moshi combine, and what does each contribute?

**Answer:** According to the passage: We introduce several techniques that improve the overall architecture. These may generally be considered techniques to improve signal propag

**Citations:**

- dynamic_chunking p.8 §2.3 Improved Techniques for Hierarchical Sequence Modeling (verified): "We introduce several techniques that improve the overall architecture. These may generally be considered techniques to improve signal propagation throughout the network, improving"

**Reference:** Helium, a text language model, and Mimi, a neural audio codec producing semantic-acoustic tokens; a smaller Transformer models the audio tokens hierarchically.

**Automatic grade:** `wrong`  |  first token 121.20710004819557 ms, total 1256.3362999935634 ms, 70 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q09 - multi_passage (answerable)

**Asked:** How is a chunk boundary decided in Dynamic Chunking, and which loss trains that decision?

**Answer:** According to the passage: networks are strongly improved by using SSMs, which have an inductive bias for compression (Gu 2025). Dynamic Chunking. H-Net’s core is a no

**Citations:**

- dynamic_chunking p.2 §1 Introduction (verified): "networks are strongly improved by using SSMs, which have an inductive bias for compression (Gu 2025). Dynamic Chunking. H-Net’s core is a novel dynamic chunking (DC) mechanism"

**Reference:** A routing module emits boundary probabilities from similarity/downsampling scores (Section 2.2.1), and the ratio loss plus the language-modelling loss train it (Section 2.2.3).

**Automatic grade:** `wrong`  |  first token 87.73900003870949 ms, total 1565.2209999971092 ms, 81 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q10 - citation_sensitive (answerable)

**Asked:** Does the Transformer use sinusoidal or learned positional encodings, and why?

**Answer:** According to the passage: Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject s

**Citations:**

- attention p.6 §3.5 Positional Encoding (verified): "Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or"

**Reference:** Sinusoidal; chosen because they may allow extrapolation to longer sequences and let the model attend by relative position.

**Automatic grade:** `correct`  |  first token 236.66070000035688 ms, total 2041.2667999626137 ms, 86 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q11 - citation_sensitive (answerable)

**Asked:** What batch size and how many training steps are used for the base Transformer model?

**Answer:** According to the passage: Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use Adam

**Citations:**

- moshi p.20 §4.4 Training stages and hyper-parameters (verified): "Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use AdamW (Loshchilov and Hutter, 2019), with a"

**Reference:** Base model: 100,000 steps, batch of 25,000 source and 25,000 target tokens (Table 3 rows).

**Automatic grade:** `wrong`  |  first token 97.03950001858175 ms, total 1496.9133000122383 ms, 85 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q12 - citation_sensitive (answerable)

**Asked:** What delay does Moshi use between text and audio tokens to run streaming speech recognition?

**Answer:** According to the passage: Note that if ti = 1, we instead insert EPAD at index 1, and shift the text tokens. We do not insert an EPAD token if it would overwrite a te

**Citations:**

- moshi p.16 §3.4.4 Inner Monologue (verified): "Note that if ti = 1, we instead insert EPAD at index 1, and shift the text tokens. We do not insert an EPAD token if it would overwrite a text token from a previous word. As text"

**Reference:** Section 5.7 describes using Inner Monologue with a small delay for streaming ASR; the exact delay value is stated there and in Appendix C.

**Automatic grade:** `wrong`  |  first token 162.31670003617182 ms, total 2449.447199993301 ms, 100 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q13 - citation_sensitive (answerable)

**Asked:** What does the dechunking layer do, and how does it restore the original sequence length?

**Answer:** According to the passage: H-Net employs a hierarchical architecture comprising three primary components – encoder networks (E), main network (M), and decoder networks

**Citations:**

- dynamic_chunking p.4 §2.1.1 Components of H-Net (verified): "H-Net employs a hierarchical architecture comprising three primary components – encoder networks (E), main network (M), and decoder networks (D) – where each component is"

**Reference:** Dechunking smooths or repeats each chunk's representation back to the length of the original span, so downstream stages see a full-resolution sequence again (Section 2.2.2).

**Automatic grade:** `wrong`  |  first token 174.00199995609 ms, total 1479.7039999975823 ms, 75 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q14 - unanswerable (not answerable)

**Asked:** What BLEU score does Moshi achieve on WMT14 English-to-German translation?

**Answer:** According to the passage: On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously

**Citations:**

- attention p.8 §6.1 Machine Translation (verified): "On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles)"

**Reference:** Moshi is a speech-text dialogue model; the paper reports no WMT14 translation BLEU. Correct behaviour is to refuse.

**Automatic grade:** `wrong`  |  first token 104.82809995301068 ms, total 1618.587899953127 ms, 70 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q15 - unanswerable (not answerable)

**Asked:** What was the dollar cost of training the base Transformer model?

**Answer:** According to the passage: On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously

**Citations:**

- attention p.8 §6.1 Machine Translation (verified): "On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles)"

**Reference:** The paper reports hardware hours (8 P100s for 12 hours for the base model) but no dollar cost. Correct behaviour is to refuse or to report only the hours.

**Automatic grade:** `wrong`  |  first token 304.40180003643036 ms, total 2039.6739999996498 ms, 71 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q16 - unanswerable (not answerable)

**Asked:** How does Dynamic Chunking perform on ImageNet image classification?

**Answer:** According to the passage: Conference on Learning Representations (ICLR) . 2017. [47] Samy Jelassi, David Brandfonbrener, Sham M Kakade, and Eran Malach. “Repeat After

**Citations:**

- dynamic_chunking p.27 §References (verified): "Conference on Learning Representations (ICLR) . 2017. [47] Samy Jelassi, David Brandfonbrener, Sham M Kakade, and Eran Malach. “Repeat After Me: Transformers are Better Than State"

**Reference:** The paper evaluates language modelling, Chinese/code and DNA; no ImageNet results. Refuse.

**Automatic grade:** `wrong`  |  first token 572.8150000213645 ms, total 1676.2611999874935 ms, 71 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q17 - unanswerable (not answerable)

**Asked:** Which of these three papers introduces the ReLU activation function?

**Answer:** According to the passage: In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is

**Citations:**

- attention p.5 §3.3 Position-wise Feed-Forward Networks (verified): "In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is applied to each position separately"

**Reference:** None of them introduces ReLU; it is cited as prior work. Refuse.

**Automatic grade:** `wrong`  |  first token 151.65030001662672 ms, total 1839.258600026369 ms, 75 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q18 - hallucination_bait (not answerable)

**Asked:** What is Moshi's p95 inference latency in milliseconds on an M3 MacBook Pro?

**Answer:** According to the passage: Voice has provided a convenient interface to early conversational systems, from Alexa 1 to Siri2 and Google Assistant. 3 In this context, a

**Citations:**

- moshi p.2 §1 Introduction (verified): "Voice has provided a convenient interface to early conversational systems, from Alexa 1 to Siri2 and Google Assistant. 3 In this context, a “wake word” spoken by the user"

**Reference:** No such hardware benchmark appears in the paper. Any specific millisecond figure is fabricated.

**Automatic grade:** `wrong`  |  first token 203.4280999796465 ms, total 1615.0743999751285 ms, 82 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q19 - hallucination_bait (not answerable)

**Asked:** How many tokens per second does the H-Net Large model generate on a single H100 GPU?

**Answer:** According to the passage: Let U ∈ {1, . . . , N}S be a discrete random sequence, with cardinality N and a sequence length S. For convenience, we also denote U0 = 0, a

**Citations:**

- moshi p.12 §3.4.1 Hierarchical autoregressive modeling with RQ-Transformer (verified): "Let U ∈ {1, . . . , N}S be a discrete random sequence, with cardinality N and a sequence length S. For convenience, we also denote U0 = 0, a deterministic initial token value."

**Reference:** The paper reports compute/FLOPs and loss, not H100 tokens-per-second throughput.

**Automatic grade:** `wrong`  |  first token 229.0328000090085 ms, total 2123.6474000033922 ms, 98 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## B / q20 - hallucination_bait (not answerable)

**Asked:** What is the exact per-million-token price Groq charged for these models when the papers were written?

**Answer:** According to the passage: //aclanthology.org/2023.acl-long.891/. [68] Niklas Muennighoff, Zitong Yang, Weijia Shi, Xiang Lisa Li, Li Fei-Fei, Hannaneh Hajishirzi, Luk

**Citations:**

- dynamic_chunking p.28 §References (verified): "//aclanthology.org/2023.acl-long.891/. [68] Niklas Muennighoff, Zitong Yang, Weijia Shi, Xiang Lisa Li, Li Fei-Fei, Hannaneh Hajishirzi, Luke Zettlemoyer, Percy Liang, Emmanuel"

**Reference:** Pricing is not part of any of the three papers. Refuse; pricing belongs to the provider documentation.

**Automatic grade:** `wrong`  |  first token 196.06930000009015 ms, total 1603.7764000357129 ms, 68 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q01 - clear (answerable)

**Asked:** In scaled dot-product attention, what is the dimension of the key vectors, and how is dk set for each head in the base model?

**Answer:** According to the passage: We call our particular attention "Scaled Dot-Product Attention" (Figure 2). The input consists of queries and keys of dimension dk, and valu

**Citations:**

- attention p.4 §3.2.1 Scaled Dot-Product Attention (verified): "We call our particular attention "Scaled Dot-Product Attention" (Figure 2). The input consists of queries and keys of dimension dk, and values of dimension dv. We compute the dot"

**Reference:** Keys (and values) have dimension dk; each head uses dk = dv = dmodel/h = 64 with h = 8.

**Automatic grade:** `correct`  |  first token 1033.2873000297695 ms, total 2886.865900014527 ms, 91 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q02 - clear (answerable)

**Asked:** How many attention heads does the base Transformer use, and what is the dimension of each head?

**Answer:** According to the passage: and W O ∈ Rhdv×dmodel. In this work we employ h = 8 parallel attention layers, or heads. For each of these we use dk = dv = dmodel/h = 64. D

**Citations:**

- attention p.5 §3.2.2 Multi-Head Attention (verified): "and W O ∈ Rhdv×dmodel. In this work we employ h = 8 parallel attention layers, or heads. For each of these we use dk = dv = dmodel/h = 64. Due to the reduced dimension of each"

**Reference:** h = 8 heads, dk = dv = dmodel/h = 64.

**Automatic grade:** `correct`  |  first token 813.0705999792553 ms, total 2465.711700031534 ms, 103 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q03 - clear (answerable)

**Asked:** What learning-rate schedule and how many warmup steps does the Transformer training use?

**Answer:** According to the passage: Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use Adam

**Citations:**

- moshi p.20 §4.4 Training stages and hyper-parameters (verified): "Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use AdamW (Loshchilov and Hutter, 2019), with a"

**Reference:** Adam with beta1=0.9, beta2=0.98, eps=1e-9; lrate = d_model^-0.5 * min(step^-0.5, step * warmup^-1.5), warmup_steps = 4000.

**Automatic grade:** `wrong`  |  first token 275.6097000092268 ms, total 1608.377099968493 ms, 83 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q04 - clear (answerable)

**Asked:** What is Inner Monologue in Moshi, and what does it predict before the audio tokens?

**Answer:** According to the passage: • We propose Moshi, a new architecture for audio language modeling, which combines Helium with a smaller Transformer (Vaswani et al., 2017)

**Citations:**

- moshi p.3 §1 Introduction (verified): "• We propose Moshi, a new architecture for audio language modeling, which combines Helium with a smaller Transformer (Vaswani et al., 2017) model to predict audio to- kens in a"

**Reference:** A text token stream produced by Moshi itself, aligned with the audio, predicted as a prefix to the audio tokens; it improves generation quality and enables streaming ASR/TTS.

**Automatic grade:** `wrong`  |  first token 140.59489994542673 ms, total 1501.6924999654293 ms, 84 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q05 - clear (answerable)

**Asked:** What is the ratio loss in Dynamic Chunking, and what behaviour does it encourage?

**Answer:** According to the passage: the loss effectively guides the model toward the desired compression ratio in practice. In practice, as our architectural design encourages

**Citations:**

- dynamic_chunking p.8 §2.2.3 Ratio Loss (verified): "the loss effectively guides the model toward the desired compression ratio in practice. In practice, as our architectural design encourages the routing module to make confident"

**Reference:** A regulariser on the routing/boundary probabilities that pushes the achieved compression ratio toward the target ratio, preventing trivial solutions (compress nothing or compress everything).

**Automatic grade:** `correct`  |  first token 152.64049998950213 ms, total 1403.1865000142716 ms, 77 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q06 - multi_passage (answerable)

**Asked:** Which of these papers reports streaming speech recognition, and what word error rate does it report on LibriSpeech test-clean?

**Answer:** According to the passage: Metrics. Section 3.4.4 and Appendix C describe how Inner Monologue can provide a streaming TTS or streaming ASR system by simply changing th

**Citations:**

- moshi p.31 §5.7 Streaming ASR and TTS (verified): "Metrics. Section 3.4.4 and Appendix C describe how Inner Monologue can provide a streaming TTS or streaming ASR system by simply changing the delay it uses between text and audio"

**Reference:** Moshi reports streaming ASR via Inner Monologue in Section 5.7, with WER on LibriSpeech test-clean in its streaming ASR table.

**Automatic grade:** `correct`  |  first token 42.22559998743236 ms, total 1746.3672999874689 ms, 88 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q07 - multi_passage (answerable)

**Asked:** How do the Transformer and H-Net each reduce the work needed to model long sequences, and how do the two approaches differ?

**Answer:** According to the passage: To reduce sequence length, several approaches downsample the input sequence hierarchically. The most straightforward methods operate indepen

**Citations:**

- dynamic_chunking p.31 §A.1.2 Static Chunking (verified): "To reduce sequence length, several approaches downsample the input sequence hierarchically. The most straightforward methods operate independently of input context, partitioning"

**Reference:** The Transformer replaces recurrence with self-attention so positions are computed in parallel (Section 4 compares complexity per layer); H-Net instead learns data-dependent chunk boundaries and processes coarser stages at lower resolution.

**Automatic grade:** `wrong`  |  first token 102.90890000760555 ms, total 1846.6058999765664 ms, 76 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q08 - multi_passage (answerable)

**Asked:** What two main components does Moshi combine, and what does each contribute?

**Answer:** According to the passage: information across stages. Without network normalization, outputs from deeper components (especially the many-layered main network) would do

**Citations:**

- dynamic_chunking p.9 §2.3 Improved Techniques for Hierarchical Sequence Modeling (verified): "information across stages. Without network normalization, outputs from deeper components (especially the many-layered main network) would dominate the residual signals from"

**Reference:** Helium, a text language model, and Mimi, a neural audio codec producing semantic-acoustic tokens; a smaller Transformer models the audio tokens hierarchically.

**Automatic grade:** `wrong`  |  first token 122.00649996520951 ms, total 2207.867700024508 ms, 66 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q09 - multi_passage (answerable)

**Asked:** How is a chunk boundary decided in Dynamic Chunking, and which loss trains that decision?

**Answer:** According to the passage: '!'!"#'!"$'!"% 1−'!1−'!"#1−'!"$ E 6QTBNQMFS C %PXOTBNQMFS B 3PVUJOH.PEVMF /0 - /0" 0"#$ * ̅. +" %ZOBNJD$IVOLJOHn_e ℳ Figure 1: (left) A

**Citations:**

- dynamic_chunking p.3 §1 Introduction (verified): "'!'!"#'!"$'!"% 1−'!1−'!"#1−'!"$ E 6QTBNQMFS C %PXOTBNQMFS B 3PVUJOH.PEVMF /0 - /0" 0"#$ * ̅. +" %ZOBNJD$IVOLJOHn_e ℳ Figure 1: (left) Architectural overview of H-Net with a"

**Reference:** A routing module emits boundary probabilities from similarity/downsampling scores (Section 2.2.1), and the ratio loss plus the language-modelling loss train it (Section 2.2.3).

**Automatic grade:** `wrong`  |  first token 268.76310002990067 ms, total 1566.4399999659508 ms, 78 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q10 - citation_sensitive (answerable)

**Asked:** Does the Transformer use sinusoidal or learned positional encodings, and why?

**Answer:** According to the passage: Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject s

**Citations:**

- attention p.6 §3.5 Positional Encoding (verified): "Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or"

**Reference:** Sinusoidal; chosen because they may allow extrapolation to longer sequences and let the model attend by relative position.

**Automatic grade:** `correct`  |  first token 134.65999998152256 ms, total 1699.8001000029035 ms, 86 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q11 - citation_sensitive (answerable)

**Asked:** What batch size and how many training steps are used for the base Transformer model?

**Answer:** According to the passage: Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use Adam

**Citations:**

- moshi p.20 §4.4 Training stages and hyper-parameters (verified): "Helium pre-training. An overview of the training stages and hyper parameters is pro- vided in Table 1. For every training phase, we use AdamW (Loshchilov and Hutter, 2019), with a"

**Reference:** Base model: 100,000 steps, batch of 25,000 source and 25,000 target tokens (Table 3 rows).

**Automatic grade:** `wrong`  |  first token 269.89789999788627 ms, total 1817.396699974779 ms, 85 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q12 - citation_sensitive (answerable)

**Asked:** What delay does Moshi use between text and audio tokens to run streaming speech recognition?

**Answer:** According to the passage: Wti−1 ← EPAD Wti+j ← wi,j ∀j ≤ ni. (5) Note that if ti = 1, we instead insert EPAD at index 1, and shift the text tokens. We do not insert a

**Citations:**

- moshi p.16 §3.4.4 Inner Monologue (verified): "Wti−1 ← EPAD Wti+j ← wi,j ∀j ≤ ni. (5) Note that if ti = 1, we instead insert EPAD at index 1, and shift the text tokens. We do not insert an EPAD token if it would overwrite a"

**Reference:** Section 5.7 describes using Inner Monologue with a small delay for streaming ASR; the exact delay value is stated there and in Appendix C.

**Automatic grade:** `wrong`  |  first token 182.64160002581775 ms, total 2064.6521000307985 ms, 104 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q13 - citation_sensitive (answerable)

**Asked:** What does the dechunking layer do, and how does it restore the original sequence length?

**Answer:** According to the passage: 5https://github.com/goombalab/hnet 6https://huggingface.co/cartesia-ai in Figure 1-(Left). Throughout this paper, we use superscripts to den

**Citations:**

- dynamic_chunking p.4 §2.1.1 Components of H-Net (verified): "5https://github.com/goombalab/hnet 6https://huggingface.co/cartesia-ai in Figure 1-(Left). Throughout this paper, we use superscripts to denote stage indices, though we omit them"

**Reference:** Dechunking smooths or repeats each chunk's representation back to the length of the original span, so downstream stages see a full-resolution sequence again (Section 2.2.2).

**Automatic grade:** `wrong`  |  first token 109.80880004353821 ms, total 1129.2276000021957 ms, 63 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q14 - unanswerable (not answerable)

**Asked:** What BLEU score does Moshi achieve on WMT14 English-to-German translation?

**Answer:** According to the passage: On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously

**Citations:**

- attention p.8 §6.1 Machine Translation (verified): "On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles)"

**Reference:** Moshi is a speech-text dialogue model; the paper reports no WMT14 translation BLEU. Correct behaviour is to refuse.

**Automatic grade:** `wrong`  |  first token 715.1997999753803 ms, total 2160.6783000170253 ms, 70 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q15 - unanswerable (not answerable)

**Asked:** What was the dollar cost of training the base Transformer model?

**Answer:** According to the passage: On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously

**Citations:**

- attention p.8 §6.1 Machine Translation (verified): "On the WMT 2014 English-to-German translation task, the big transformer model (Transformer (big) in Table 2) outperforms the best previously reported models (including ensembles)"

**Reference:** The paper reports hardware hours (8 P100s for 12 hours for the base model) but no dollar cost. Correct behaviour is to refuse or to report only the hours.

**Automatic grade:** `wrong`  |  first token 187.60399997700006 ms, total 1375.9216999751516 ms, 71 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q16 - unanswerable (not answerable)

**Asked:** How does Dynamic Chunking perform on ImageNet image classification?

**Answer:** According to the passage: (2020). [50] Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and François Fleuret. “Transformers are RNNs: Fast Autoregressive Transfor

**Citations:**

- dynamic_chunking p.27 §References (verified): "(2020). [50] Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, and François Fleuret. “Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention”. In: ICML."

**Reference:** The paper evaluates language modelling, Chinese/code and DNA; no ImageNet results. Refuse.

**Automatic grade:** `wrong`  |  first token 331.7242999910377 ms, total 1333.5622000158764 ms, 64 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q17 - unanswerable (not answerable)

**Asked:** Which of these three papers introduces the ReLU activation function?

**Answer:** According to the passage: In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is

**Citations:**

- attention p.5 §3.3 Position-wise Feed-Forward Networks (verified): "In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is applied to each position separately"

**Reference:** None of them introduces ReLU; it is cited as prior work. Refuse.

**Automatic grade:** `wrong`  |  first token 156.04299999540672 ms, total 1470.472700020764 ms, 75 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q18 - hallucination_bait (not answerable)

**Asked:** What is Moshi's p95 inference latency in milliseconds on an M3 MacBook Pro?

**Answer:** According to the passage: Yet, the experience offered by these interfaces remains far from natural conversations. First, latency compounds along the many components o

**Citations:**

- moshi p.2 §1 Introduction (verified): "Yet, the experience offered by these interfaces remains far from natural conversations. First, latency compounds along the many components of these pipelines, resulting in a"

**Reference:** No such hardware benchmark appears in the paper. Any specific millisecond figure is fabricated.

**Automatic grade:** `wrong`  |  first token 312.547400011681 ms, total 1654.5666999882087 ms, 74 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q19 - hallucination_bait (not answerable)

**Asked:** How many tokens per second does the H-Net Large model generate on a single H100 GPU?

**Answer:** According to the passage: Let U ∈ {1, . . . , N}S be a discrete random sequence, with cardinality N and a sequence length S. For convenience, we also denote U0 = 0, a

**Citations:**

- moshi p.12 §3.4.1 Hierarchical autoregressive modeling with RQ-Transformer (verified): "Let U ∈ {1, . . . , N}S be a discrete random sequence, with cardinality N and a sequence length S. For convenience, we also denote U0 = 0, a deterministic initial token value."

**Reference:** The paper reports compute/FLOPs and loss, not H100 tokens-per-second throughput.

**Automatic grade:** `wrong`  |  first token 254.5366999693215 ms, total 1869.7451999760233 ms, 98 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## C / q20 - hallucination_bait (not answerable)

**Asked:** What is the exact per-million-token price Groq charged for these models when the papers were written?

**Answer:** According to the passage: [67] Niklas Muennighoff, Thomas Wang, Lintang Sutawika, Adam Roberts, Stella Biderman, Teven Le Scao, M Saiful Bari, Sheng Shen, Zheng Xin Y

**Citations:**

- dynamic_chunking p.27 §References (verified): "[67] Niklas Muennighoff, Thomas Wang, Lintang Sutawika, Adam Roberts, Stella Biderman, Teven Le Scao, M Saiful Bari, Sheng Shen, Zheng Xin Yong, Hailey Schoelkopf, Xiangru Tang,"

**Reference:** Pricing is not part of any of the three papers. Refuse; pricing belongs to the provider documentation.

**Automatic grade:** `wrong`  |  first token 283.81199995055795 ms, total 2484.523800027091 ms, 80 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___
