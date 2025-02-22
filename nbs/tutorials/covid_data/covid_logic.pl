Lemmas(P,D,Word,Lem)<-Docs(P,D,"raw_text"),lemma(D)->(Word,Lem).

LemmaConceptMatches(Path,Doc,Span,Label) <- 
    Docs(Path,Doc,"lemma"),
    ConceptTagRules(Pattern, Label, "lemma"),
    rgx(Pattern,Doc) -> (Span).

# here we get the spans of all POS
Pos(P,D,Word,Lem)<-Docs(P,D,"lemma_concept"),pos(D)->(Word,Lem).

# here we look for concept rule matches where the matched word is also tagged via POS
PosConceptMatches(Path,Doc,Span,Label) <- 
    Docs(Path,Doc,"lemma_concept"),
    ConceptTagRules(Pattern, Label, "pos"),
    rgx(Pattern,Doc) -> (Span),
    Pos(Path,Doc,Span,POSLabel).

TargetMatches(Path,Doc, Span, Label) <- 
    Docs(Path,Doc,"pos_concept"),
    TargetTagRules(Pattern, Label), rgx(Pattern,Doc) -> (Span).

# we get section spans and their content using our regex pattern and the rgx_split ie function
Sections(P,D,Sec,Content)<-Docs(P,D,"target_concept"),
    rgx_split($section_delimeter_pattern,D)->(SecSpan,Content),
    as_str(SecSpan)->(Sec).

PositiveSections(P,D,Sec,Content)<-Sections(P,D,Sec,Content),SectionTags(Sec,Tag),PositiveSectionTags(Tag).

Sents(P,S)<-Docs(P,D,"target_concept"),split_sentence(D)->(S).

# first we get the covid mentions and their surrounding sentences, using the span_contained ie function
CovidMentions(Path, Span) <- Docs(Path,D,"target_concept"), rgx("COVID-19",D) -> (Span).
CovidMentionSents(P,Mention,Sent)<-CovidMentions(P,Mention),Sents(P,Sent),span_contained(Mention,Sent)->(True).

