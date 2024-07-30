Lemmas(P,D,Word,Lem)<-Docs(P,D,"raw_text"),lemma(D)->(Word,Lem)

LemmaConceptMatches(Path,Doc,Span,Label) <- \
    Docs(Path,Doc,"lemma"),\
    ConceptTagRules(Pattern, Label, "lemma"),\
    rgx(Pattern,Doc) -> (Span)

# here we get the spans of all POS
Pos(P,D,Word,Lem)<-Docs(P,D,"lemma_concept"),pos(D)->(Word,Lem)

# here we look for concept rule matches where the matched word is also tagged via POS
PosConceptMatches(Path,Doc,Span,Label) <- \
    Docs(Path,Doc,"lemma_concept"),\
    ConceptTagRules(Pattern, Label, "pos"),\
    rgx(Pattern,Doc) -> (Span),\
    Pos(Path,Doc,Span,POSLabel)

TargetMatches(Path,Doc, Span, Label) <- \
    Docs(Path,Doc,"pos_concept"),\
    TargetTagRules(Pattern, Label), rgx(Pattern,Doc) -> (Span)

# we get section spans and their content using our regex pattern and the rgx_split ie function
Sections(P,D,Sec,Content)<-Docs(P,D,"target_concept"),\
    rgx_split($section_delimeter_pattern,D)->(SecSpan,Content),\
    as_str(SecSpan)->(Sec)

PositiveSections(P,D,Sec,Content)<-Sections(P,D,Sec,Content),SectionTags(Sec,Tag),PositiveSectionTags(Tag)

Sents(P,S)<-Docs(P,D,"target_concept"),split_sentence(D)->(S)

SentPairs(P,S1,S2)<-Sents(P,S1),Sents(P,S2),expr_eval("{0}.end +1 == {1}.start",S1,S2)->(True)

# first we get the covid mentions and their surrounding sentences, using the span_contained ie function
CovidMentions(Path, Span) <- Docs(Path,D,"target_concept"), rgx("COVID-19",D) -> (Span)
CovidMentionSents(P,Mention,Sent)<-CovidMentions(P,Mention),Sents(P,Sent),span_contained(Mention,Sent)->(True)


# note that for ease of debugging, we extended our head to track which rule a fact was derived from

# a tag is positive if it is contained in a positive section
CovidTags(Path,Mention,'positive','section')<-\
    PositiveSections(Path,D,Title,Section),\
    CovidMentions(Path,Mention),\
    span_contained(Mention,Section)->(True)

# Context rules tags
CovidTags(Path,Mention,Tag,'sentence context')<-\
    CovidMentionSents(Path,Mention,Sent),\
    SentenceContextRules(Pattern,Tag),\
    rgx(Pattern,Sent)->(ContextSpan),\
    span_contained(Mention,ContextSpan)->(True)

# post processing based on pattern
CovidTags(Path,Mention,Tag,'post pattern')<-\
    CovidMentionSents(Path,Mention,Sent),\
    PostprocessPatternRules(Pattern,Tag),\
    rgx(Pattern,Sent)->(ContextSpan),\
    span_contained(Mention,ContextSpan)->(True)

# post processing based on pattern and existing attributes
# notice the recursive call to CovidTags
CovidTags(Path,Mention,Tag,"post attribute change")<-\
    CovidTags(Path,Mention,OldTag,Derivation),\
    PostprocessRulesWithAttributes(Pattern,OldTag,Tag),\
    CovidMentionSents(Path,Mention,Sent),\
    rgx(Pattern,Sent)->(ContextSpan),\
    span_contained(Mention,ContextSpan)->(True)

# post processing based on pattern in the next sentence
CovidTags(Path,Mention,Tag,"next sentence")<-\
    CovidMentionSents(Path,Mention,Sent),\
    SentPairs(Path,Sent,NextSent),\
    PostprocessPatternRules(Pattern,Tag),\
    rgx(Pattern,NextSent)->(ContextSpan)

AggregatedCovidTags(Path,Mention,agg_mention(Tag))<-\
    CovidTags(Path,Mention,Tag,Derivation)

DocumentTags(Path,agg_doc_tags(Tag))<-\
    AggregatedCovidTags(Path,Mention,Tag)

