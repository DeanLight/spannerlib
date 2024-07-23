
RawDocs(P,D,'raw_text')<-Files(P),read(P)->(D)

Lemmas(P,D,Word,Lem)<-Docs(P,D,"raw_text"),lemma(D)->(Word,Lem)

LemmaConceptMatches(Path,Doc,Span,Label) <- \
    Docs(Path,Doc,"lemma"),\
    ConceptTagRules(Pattern, Label, "lemma"),\
    rgx(Pattern,Doc) -> (Span)

# here we get the spans of all POS
Pos(P,D,Word,Lem)<-Docs(P,D,"lemma_concept"),pos(D)->(Word,Lem)
# small debugging print helps in building new rules
# here we look for concept rule matches where the matched word is also tagged via POS
PosConceptMatches(Path,Doc,Span,Label) <- \
    Docs(Path,Doc,"lemma_concept"),\
    ConceptTagRules(Pattern, Label, "pos"),\
    rgx(Pattern,Doc) -> (Span),\
    Pos(Path,Doc,Span,POSLabel)

TargetMatches(Path,Doc, Span, Label) <- \
    Docs(Path,Doc,"pos_concept"),\
    TargetTagRules(Pattern, Label), rgx(Pattern,Doc) -> (Span)

Sections(P,D,Sec,Content)<-Docs(P,D,"target_concept"),\
    rgx_split($section_delimeter_pattern,D)->(SecSpan,Content),\
    as_str(SecSpan)->(Sec)

PositiveSections(P,D,Sec,Content)<-Sections(P,D,Sec,Content),SectionTags(Sec,Tag),PositiveSectionTags(Tag)

Sents(P,S)<-Docs(P,D,"target_concept"),split_sentence(D)->(S)

SentPairs(P,S1,S2)<-Sents(P,S1),Sents(P,S2),expr_eval("{0}.end +1 == {1}.start",S1,S2)->(True)

CovidMentions(Path, Span) <- Docs(Path,D,"target_concept"), rgx("COVID-19",D) -> (Span)
CovidMentionSents(P,Mention,Sent)<-CovidMentions(P,Mention),Sents(P,Sent),span_contained(Mention,Sent)->(True)


CovidTags(Path,Mention,'positive','section')<-\
    PositiveSections(Path,D,Title,Section),\
    CovidMentions(Path,Mention),\
    span_contained(Mention,Section)->(True)

#covid_attributes: negated, other_experiencer, is_future, not_relevant, uncertain, positive
CovidTags(Path,Mention,Tag,'sentence context')<-\
    CovidMentionSents(Path,Mention,Sent),\
    SentenceContextRules(Pattern,Tag),\
    rgx(Pattern,Sent)->(ContextSpan),\
    span_contained(Mention,ContextSpan)->(True)

CovidTags(Path,Mention,Tag,'post pattern')<-\
    CovidMentionSents(Path,Mention,Sent),\
    PostprocessPatternRules(Pattern,Tag),\
    rgx(Pattern,Sent)->(ContextSpan),\
    span_contained(Mention,ContextSpan)->(True)

CovidTags(Path,Mention,Tag,"post attribute change")<-\
    CovidTags(Path,Mention,OldTag,Derivation),\
    PostprocessRulesWithAttributes(Pattern,OldTag,Tag),\
    CovidMentionSents(Path,Mention,Sent),\
    rgx(Pattern,Sent)->(ContextSpan),\
    span_contained(Mention,ContextSpan)->(True)


CovidTags(Path,Mention,Tag,"next sentence")<-\
    CovidMentionSents(Path,Mention,Sent),\
    SentPairs(Path,Sent,NextSent),\
    PostprocessPatternRules(Pattern,Tag),\
    rgx(Pattern,NextSent)->(ContextSpan)

# TODO why dont we see the docid in the span
AggregatedCovidTags(Path,Mention,agg_mention(Tag))<-\
    CovidTags(Path,Mention,Tag,Derivation)

DocumentTags(Path,agg_doc_tags(Tag))<-\
    AggregatedCovidTags(Path,Mention,Tag)

