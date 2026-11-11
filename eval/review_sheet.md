# Manual grading sheet

Source: real. final_grade: correct | wrong | refused_correctly | refused_wrongly | leave blank to keep the automatic grade. evidence_support: supported | partly | unsupported. citation_correct: yes | no | n/a. abstention_correct: yes | no | n/a.

Grade against the papers, not against the reference answer alone: the reference is
a pointer to the right region, and a correct answer may be worded differently.

## A / q01 - clear (answerable)

**Asked:** In scaled dot-product attention, what is the dimension of the key vectors, and how is dk set for each head in the base model?

**Answer:** The key vectors have dimension dk. In the base model with h = 8 heads, each head uses dk = dmodel/h = 64 (so dk = dv = 64 per head).

**Citations:**

- attention p.4 §3.2.1 Scaled Dot-Product Attention (verified): "The input consists of queries and keys of dimension dk, and values of dimension dv."
- attention p.5 §3.2.2 Multi-Head Attention (verified): "For each of these we use dk = dv = dmodel/h = 64."

**Reference:** Keys (and values) have dimension dk; each head uses dk = dv = dmodel/h = 64 with h = 8.

**Automatic grade:** `correct`  |  first token 891.7519999668002 ms, total 2862.8886999795213 ms, 615 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q02 - clear (answerable)

**Asked:** How many attention heads does the base Transformer use, and what is the dimension of each head?

**Answer:** The base Transformer uses 8 attention heads, each with a dimension of 64.

**Citations:**

- attention p.5 §3.2.2 Multi-Head Attention (verified): "In this work we employ h = 8 parallel attention layers, or heads. For each of these we use dk = dv = dmodel/h = 64."

**Reference:** h = 8 heads, dk = dv = dmodel/h = 64.

**Automatic grade:** `correct`  |  first token 984.8963000113145 ms, total 3688.2339000003412 ms, 486 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q03 - clear (answerable)

**Asked:** What learning-rate schedule and how many warmup steps does the Transformer training use?

**Answer:** I drafted an answer but could not verify its quotations against the papers, so I am not sending it. A wrong citation is worse than no answer here.

**Citations:**

- none

**Reference:** Adam with beta1=0.9, beta2=0.98, eps=1e-9; lrate = d_model^-0.5 * min(step^-0.5, step * warmup^-1.5), warmup_steps = 4000.

**Automatic grade:** `refused_wrongly`  |  first token 994.39170002006 ms, total 59017.71539996844 ms, 1880 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q04 - clear (answerable)

**Asked:** What is Inner Monologue in Moshi, and what does it predict before the audio tokens?

**Answer:** Inner Monologue is a component of Moshi that generates text tokens as a prefix before the audio tokens, i.e., it predicts a sequence of text tokens prior to producing the corresponding audio tokens. This adds an extra token per multi‑stream timestep, increasing the generation from 16 to 17 tokens.

**Citations:**

- moshi p.26 §5.3 Ablations on generative modeling (verified): "modeling text tokens as a prefix to audio tokens with Inner Monologue"
- moshi p.29 §5.5 Spoken question answering (verified): "each multi-stream timestep requires generating 17 tokens, instead of 16 without Inner Monologue"

**Reference:** A text token stream produced by Moshi itself, aligned with the audio, predicted as a prefix to the audio tokens; it improves generation quality and enables streaming ASR/TTS.

**Automatic grade:** `wrong`  |  first token 907.0568999741226 ms, total 3834.3880999600515 ms, 784 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q05 - clear (answerable)

**Asked:** What is the ratio loss in Dynamic Chunking, and what behaviour does it encourage?

**Answer:** I drafted an answer but could not verify its quotations against the papers, so I am not sending it. A wrong citation is worse than no answer here.

**Citations:**

- none

**Reference:** A regulariser on the routing/boundary probabilities that pushes the achieved compression ratio toward the target ratio, preventing trivial solutions (compress nothing or compress everything).

**Automatic grade:** `refused_wrongly`  |  first token 623.8197999773547 ms, total 53917.08199994173 ms, 854 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q06 - multi_passage (answerable)

**Asked:** Which of these papers reports streaming speech recognition, and what word error rate does it report on LibriSpeech test-clean?

**Answer:** I drafted an answer but could not verify its quotations against the papers, so I am not sending it. A wrong citation is worse than no answer here.

**Citations:**

- none

**Reference:** Moshi reports streaming ASR via Inner Monologue in Section 5.7, with WER on LibriSpeech test-clean in its streaming ASR table.

**Automatic grade:** `refused_wrongly`  |  first token 2989.2182999756187 ms, total 5978.378599975258 ms, 1698 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q07 - multi_passage (answerable)

**Asked:** How do the Transformer and H-Net each reduce the work needed to model long sequences, and how do the two approaches differ?

**Answer:** The Transformer reduces the work of modeling long sequences by using multi‑head self‑attention that processes many positions in parallel and by masking out illegal connections, so each layer can attend to all relevant tokens without sequential recurrence. H‑Net reduces work by learning dynamic chunking boundaries that compress low‑information regions while keeping high‑information content, allowing the model to allocate computation adaptively to fewer, larger chunks. Thus, the Transformer operates at the token level with parallel attention, whereas H‑Net changes the sequence length itself through adaptive chunking.

**Citations:**

- attention p.3 §3.2 Attention (verified): "Multi-Head Attention consists of several attention layers running in parallel."
- attention p.5 §3.2.3 Applications of Attention in our Model (verified): "We implement this inside of scaled dot-product attention by masking out (setting to −∞) all values in the input of the softmax which correspond to illegal connections."
- dynamic_chunking p.6 §2.2 Dynamic Chunking (DC) (verified): "this dynamic approach enables the model to allocate computational resources efficiently by compressing low-information regions while preserving high-information content at appropriate granularity."

**Reference:** The Transformer replaces recurrence with self-attention so positions are computed in parallel (Section 4 compares complexity per layer); H-Net instead learns data-dependent chunk boundaries and processes coarser stages at lower resolution.

**Automatic grade:** `correct`  |  first token 1269.5490999612957 ms, total 56080.46730002388 ms, 890 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q08 - multi_passage (answerable)

**Asked:** What two main components does Moshi combine, and what does each contribute?

**Answer:** Moshi combines Helium, a 7‑billion‑parameter text language model pretrained on 2.1 trillion tokens, which provides the textual understanding, with a smaller Transformer that predicts the audio stream, handling the speech generation side of the system.

**Citations:**

- moshi p.2 §1 Introduction (verified): "We present Helium, a 7B-parameter text LLM that we pretrain on 2 .1T tokens of public English data."
- moshi p.2 §1 Introduction (verified): "We propose Moshi, a new architecture for audio language modeling, which combines Helium with a smaller Transformer (Vaswani et al., 2017) model to predict audio"

**Reference:** Helium, a text language model, and Mimi, a neural audio codec producing semantic-acoustic tokens; a smaller Transformer models the audio tokens hierarchically.

**Automatic grade:** `wrong`  |  first token 758.9006999041885 ms, total 2194.025299977511 ms, 657 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q09 - multi_passage (answerable)

**Asked:** How is a chunk boundary decided in Dynamic Chunking, and which loss trains that decision?

**Answer:** Chunk boundaries are produced by a routing module that outputs boundary probabilities, effectively drawing chunk boundaries dynamically. The decision is trained with a binary cross‑entropy boundary‑prediction loss applied to those probabilities, encouraging the router to pass the start of each real token through the main network.

**Citations:**

- dynamic_chunking p.3 §1 Introduction (verified): "Key components of a chunking layer: (a) a routing module for dynamically drawing chunk boundaries, and (b) a downsampler that selectively retains vectors based on boundary indicators"
- dynamic_chunking p.38 §F Distilling Token-Level Models to Byte-Level (verified): "A binary cross-entropy boundary-prediction loss (with equal weight as the main loss) that operates on the routing module probabilities and targets the router to pass the start of every real token through the main network."

**Reference:** A routing module emits boundary probabilities from similarity/downsampling scores (Section 2.2.1), and the ratio loss plus the language-modelling loss train it (Section 2.2.3).

**Automatic grade:** `wrong`  |  first token 1061.8875999934971 ms, total 3632.988999946974 ms, 896 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q10 - citation_sensitive (answerable)

**Asked:** Does the Transformer use sinusoidal or learned positional encodings, and why?

**Answer:** I drafted an answer but could not verify its quotations against the papers, so I am not sending it. A wrong citation is worse than no answer here.

**Citations:**

- none

**Reference:** Sinusoidal; chosen because they may allow extrapolation to longer sequences and let the model attend by relative position.

**Automatic grade:** `refused_wrongly`  |  first token 777.2742999950424 ms, total 58296.41049995553 ms, 1510 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q11 - citation_sensitive (answerable)

**Asked:** What batch size and how many training steps are used for the base Transformer model?

**Answer:** The base Transformer model uses a batch size of 256 and is trained for 100,000 steps.

**Citations:**

- dynamic_chunking p.11 §3 Experiments (verified): "We use batch size 256 for all models; the total batch size is just under 0.5M tokens per batch for the baseline BPE Transformer..."
- attention p.7 §5.2 Hardware and Schedule (verified): "We trained the base models for a total of 100,000 steps or 12 hours."

**Reference:** Base model: 100,000 steps, batch of 25,000 source and 25,000 target tokens (Table 3 rows).

**Automatic grade:** `wrong`  |  first token 599.6162000810727 ms, total 2392.817199928686 ms, 709 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q12 - citation_sensitive (answerable)

**Asked:** What delay does Moshi use between text and audio tokens to run streaming speech recognition?

**Answer:** The papers do not state this.

**Citations:**

- none

**Reference:** Section 5.7 describes using Inner Monologue with a small delay for streaming ASR; the exact delay value is stated there and in Appendix C.

**Automatic grade:** `refused_wrongly`  |  first token 580.6244999403134 ms, total 51949.93530004285 ms, 357 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q13 - citation_sensitive (answerable)

**Asked:** What does the dechunking layer do, and how does it restore the original sequence length?

**Answer:** I drafted an answer but could not verify its quotations against the papers, so I am not sending it. A wrong citation is worse than no answer here.

**Citations:**

- none

**Reference:** Dechunking smooths or repeats each chunk's representation back to the length of the original span, so downstream stages see a full-resolution sequence again (Section 2.2.2).

**Automatic grade:** `refused_wrongly`  |  first token 619.4141999585554 ms, total 4292.982299928553 ms, 869 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q14 - unanswerable (not answerable)

**Asked:** What BLEU score does Moshi achieve on WMT14 English-to-German translation?

**Answer:** The papers do not state this.

**Citations:**

- none

**Reference:** Moshi is a speech-text dialogue model; the paper reports no WMT14 translation BLEU. Correct behaviour is to refuse.

**Automatic grade:** `refused_correctly`  |  first token 916.1359000718221 ms, total 2890.8330999547616 ms, 286 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q15 - unanswerable (not answerable)

**Asked:** What was the dollar cost of training the base Transformer model?

**Answer:** The papers do not state this.

**Citations:**

- none

**Reference:** The paper reports hardware hours (8 P100s for 12 hours for the base model) but no dollar cost. Correct behaviour is to refuse or to report only the hours.

**Automatic grade:** `refused_correctly`  |  first token 1582.847599987872 ms, total 54462.821700028144 ms, 491 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q16 - unanswerable (not answerable)

**Asked:** How does Dynamic Chunking perform on ImageNet image classification?

**Answer:** The three papers in this library do not cover that. I only answer from Attention Is All You Need, Moshi, and Dynamic Chunking.

**Citations:**

- none

**Reference:** The paper evaluates language modelling, Chinese/code and DNA; no ImageNet results. Refuse.

**Automatic grade:** `refused_correctly`  |  first token 1963.6324000312015 ms, total 2005.0784000195563 ms, 287 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q17 - unanswerable (not answerable)

**Asked:** Which of these three papers introduces the ReLU activation function?

**Answer:** The attention paper (Attention Is All You Need) introduces the ReLU activation function in its feed‑forward network.

**Citations:**

- attention p.5 §3.3 Position-wise Feed-Forward Networks (verified): "This consists of two linear transformations with a ReLU activation in between."

**Reference:** None of them introduces ReLU; it is cited as prior work. Refuse.

**Automatic grade:** `wrong`  |  first token 1118.7212000368163 ms, total 2267.6226999610662 ms, 555 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q18 - hallucination_bait (not answerable)

**Asked:** What is Moshi's p95 inference latency in milliseconds on an M3 MacBook Pro?

**Answer:** The papers do not state this.

**Citations:**

- none

**Reference:** No such hardware benchmark appears in the paper. Any specific millisecond figure is fabricated.

**Automatic grade:** `refused_correctly`  |  first token 1048.2191999908537 ms, total 2353.7860999349505 ms, 473 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q19 - hallucination_bait (not answerable)

**Asked:** How many tokens per second does the H-Net Large model generate on a single H100 GPU?

**Answer:** The papers do not state this.

**Citations:**

- none

**Reference:** The paper reports compute/FLOPs and loss, not H100 tokens-per-second throughput.

**Automatic grade:** `refused_correctly`  |  first token 902.6235999772325 ms, total 53061.95539992768 ms, 433 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___

## A / q20 - hallucination_bait (not answerable)

**Asked:** What is the exact per-million-token price Groq charged for these models when the papers were written?

**Answer:** The three papers in this library do not cover that. I only answer from Attention Is All You Need, Moshi, and Dynamic Chunking.

**Citations:**

- none

**Reference:** Pricing is not part of any of the three papers. Refuse; pricing belongs to the provider documentation.

**Automatic grade:** `refused_correctly`  |  first token 653.0761000467464 ms, total 662.5366000225767 ms, 163 tokens out

Fill in: final_grade ___ evidence_support ___ citation_correct ___ abstention_correct ___ notes ___
