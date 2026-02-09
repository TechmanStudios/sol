STOPWORDS = {
    # Core English
    'a','about','above','after','again','against','all','am','an','and','any','are','as','at',
    'be','because','been','before','being','below','between','both','but','by',
    'can','could',
    'cannot',
    'did','do','does','doing','down','during',
    'each','either','else','enough',
    'few','for','from','further',
    'had','has','have','having','he','her','here','hers','herself','him','himself','his','how',
    'i','if','in','into','is','it','its','itself',
    'just',
    'me','more','most','my','myself',
    'no','nor','not','now',
    'of','off','on','once','only','or','other','our','ours','ourselves','out','over','own',
    'same','she','should','so','some','such',
    'than','that','the','their','theirs','them','themselves','then','there','these','they','this','those','through','to','too',
    'under','until','up',
    'very',
    'was','we','were','what','when','where','which','while','who','whom','why','with','would',
    'you','your','yours','yourself','yourselves',

    # Extra high-frequency glue words (keep the sculpture less "Englishy")
    'one','two','three','four','five','six','seven','eight','nine','ten',
    'first','second','third','next','last',
    'many','much','more','most','less','least',
    'another','others','somebody','someone','something',
    'may','might','must','shall','will','would','should','could',
    'also','however','therefore','thus','hence',
    'within','without','across','among','around','toward','towards','upon','onto',
    'via','per','etc',

    # Markdown / boilerplate / export noise
    'generated','utc','type','txt','pdf','rtf','verbatim','source','manifest','file','size','sha256',
    'lines','omitted','copyright','rights','reserved','www','http','https','com',
    'substack','newsletter','subscribe','subscriptions',

    # Very common corpus tokens that don’t help sculpt meaning
    'volume','issue','page','chapter','section','figure','table','example','note',
}
