"""Conteúdo textual dos dados de demonstração (EV-08): só dados, sem lógica.

Cada sessão é uma lista de blocos (um por pergunta central) com pares
(fala do participante, aprofundamento do entrevistador). Aprofundamento None
significa que o entrevistador avança para a próxima pergunta (ou encerra).
Uma sessão em andamento termina num aprofundamento sem resposta, ou num
bloco vazio (pergunta feita e ainda não respondida).
"""

T = "demo-transporte"
S = "demo-saude"
A = "demo-aplicativo"
G = "entrevista-generalista"

# (id, apelido, faixa_etaria, regiao, canal)
PARTICIPANTS = [
    ("demo-p01", "Dona Sônia", "45-54", "Jardim Alvorada, Maringá", "voz"),
    ("demo-p02", "Lucas", "18-24", "Sarandi", "texto"),
    ("demo-p03", "Seu Antônio", "65 ou mais", "Paiçandu", "voz"),
    ("demo-p04", "Cris", "35-44", "Zona rural, Marialva", "voz"),
    ("demo-p05", "Rosa", "45-54", "Vila Operária, Maringá", "voz"),
    ("demo-p06", "Aline", "25-34", "Sarandi", "texto"),
    ("demo-p07", "Seu João", "65 ou mais", "Zona rural, Floresta", "voz"),
    ("demo-p08", "Rafa", "25-34", "Maringá, zona norte", "voz"),
    ("demo-p09", "Dani", "35-44", "Sarandi", "voz"),
    ("demo-p10", None, "18-24", "Paiçandu", "texto"),
]

# when = (dia relativo à data-base, hora, minuto)
SESSION_SPECS = [
    {
        "n": 1, "script": T, "participant": "demo-p01", "when": (0, 10, 15),
        "profile": {"ocupacao": "diarista", "contexto": "mora no Jardim Alvorada e usa ônibus duas vezes ao dia", "sentimento": "cansada, mas resignada"},
        "blocks": [
            [("Eu moro no Jardim Alvorada, aqui em Maringá. Trabalho de diarista, limpo casa no centro. Saio de casa umas cinco e meia pra chegar às sete.", None)],
            [("Foi ontem. Esperei o ônibus quarenta minutos no ponto, que não tem cobertura, tava garoando. Quando veio tava lotado, fui em pé até o terminal.", "Quarenta minutos no ponto, debaixo de garoa. E o que você faz enquanto espera?"),
             ("Fico olhando o celular pra ver se o ônibus já passou, mas o aplicativo nunca acerta. Aí fico rezando pra não perder o horário, porque se eu chego atrasada a patroa desconta.", None)],
            [("O tempo. E o preço também, né, que passou pra cinco e dez a passagem.", "O tempo e o preço. Qual dos dois pesa mais no seu mês?"),
             ("O preço. No fim do mês, só de passagem vai uns trezentos e pouco do que eu ganho. É quase uma diária por semana só pra ir trabalhar.", None)],
            [("Já. Já perdi diária por causa de ônibus que não passou. E também deixei de levar meu filho no posto de saúde uma vez.", "Você falou do posto de saúde com seu filho. Pode me contar como foi isso?"),
             ("Ele tava com febre alta, de manhã. O ônibus do bairro só passa de hora em hora, e eu fui a pé até a avenida com ele no colo. Acabei chegando quase meio-dia, ele já tava pior.", None)],
            [("Colocar mais horário de ônibus de manhã cedo e de noite. E um ponto com telhado, só isso já ajudava muito.", None)],
        ],
    },
    {
        "n": 2, "script": T, "participant": "demo-p02", "when": (1, 19, 40),
        "profile": {"ocupacao": "estudante e atendente de loja", "contexto": "estuda à noite em Maringá e mora em Sarandi", "sentimento": "preocupado com segurança"},
        "blocks": [
            [("Moro em Sarandi, faço faculdade em Maringá à noite e trabalho de dia numa loja. Vou de ônibus intermunicipal.", None)],
            [("Ontem voltei da aula e o último ônibus pra Sarandi sai 23h10. Perdi por 2 min e fiquei esperando até 0h30.", "Perdeu por dois minutos e ficou esperando até meia-noite e meia. Como foi esse tempo esperando?"),
             ("Fiquei no terminal, quase vazio, com um pouco de medo. Chamei meu pai pra vir me buscar, mas ele tinha que acordar 5h.", None)],
            [("Segurança e horário. De noite o ponto é escuro e quase não tem ninguém.", None)],
            [("Sim, já faltei em prova por causa disso.", "Faltou em prova. O que aconteceu nesse dia?"),
             ("O ônibus quebrou no caminho e não colocaram outro. Cheguei 40 min depois do início e o professor não deixou entrar.", None)],
            [("Mais ônibus de madrugada e um passe estudantil que funcione também nas linhas intermunicipais.", None)],
        ],
    },
    {
        "n": 3, "script": T, "participant": "demo-p03", "when": (3, 7, 30),
        "profile": {"ocupacao": "aposentado (construção civil)", "contexto": "idoso com problema no joelho, usa ônibus para ir ao médico", "sentimento": "inseguro"},
        "blocks": [
            [("Eu moro em Paiçandu há trinta anos. Sou aposentado, trabalhei em obra a vida toda. Hoje saio pouco, só pro médico e pra pegar a aposentadoria.", None)],
            [("Fui na semana passada pro hospital em Maringá. Peguei o ônibus às sete, o motorista demorou pra parar e eu quase caí quando ele arrancou.", "Quase caiu quando o ônibus arrancou. Como foi isso?"),
             ("Eu tenho problema no joelho, né. Subi devagar e ele já tava saindo. Ninguém me ajudou, só uma moça que me segurou.", None)],
            [("A lotação. E as escadas altas do ônibus, pra gente velho é difícil.", None)],
            [("Já deixei consulta por causa disso. Ficava com medo de ir sozinho e meu filho trabalha.", "Você deixou de ir à consulta por medo de ir sozinho. Isso aconteceu mais de uma vez?"),
             ("Umas três vezes esse ano. Remarcar demora meses, aí a dor piora.", None)],
            [("Ônibus com piso baixo e motorista com mais paciência. Parece pouco, mas muda tudo pra quem é idoso.", None)],
        ],
    },
    {
        "n": 4, "script": T, "participant": "demo-p04", "when": (4, 12, 10),
        "profile": {"ocupacao": "trabalhadora rural (colheita)", "contexto": "mora no sítio, um ônibus por dia para a cidade"},
        "blocks": [
            [("Moro no sítio, no distrito perto de Marialva. Trabalho na colheita e tenho três filhos na escola.", None)],
            [("O ônibus escolar passa às 6h, mas pra gente ir pra cidade só tem um ônibus por dia. Da última vez que fui, voltei de carona.", "Voltou de carona. Como foi arrumar essa carona?"),
             ("Fiquei esperando no ponto até o vizinho passar. Se ele não passasse eu dormia na cidade, na casa da minha irmã.", None)],
            [("Falta de horário.", "Falta de horário. Me explica melhor o que isso significa na sua rotina?")],
        ],
    },
    {
        "n": 5, "script": T, "participant": None, "when": (6, 18, 5),
        "profile": {"ocupacao": "vendedora de marmitas", "contexto": "usa ônibus com mercadoria", "sentimento": "constrangida"},
        "blocks": [
            [("Moro no Conjunto Requião, vendo marmita pros vizinhos e quando dá eu pego ônibus pra comprar ingrediente no mercado grande.", None)],
            [("Foi sábado. Peguei o ônibus com as sacolas, o motorista reclamou do volume e eu fiquei sem graça.", "Ele reclamou do volume e você ficou sem graça. O que você sentiu naquela hora?"),
             ("Vergonha, né. Eu tava só trabalhando. Parece que a gente que carrega peso não é bem-vinda no ônibus.", None)],
            [("O preço, porque eu tenho que ir e voltar com a mercadoria. Não compensa muito.", None)],
            [("Já deixei de buscar encomenda grande porque não dava pra levar de ônibus.", None)],
            [("Um espaço pra bagagem nos ônibus e uma tarifa menor pra quem usa pra trabalhar.", None)],
        ],
    },
    {
        "n": 6, "script": S, "participant": "demo-p05", "when": (7, 9, 20),
        "profile": {"ocupacao": "cuidadora de idosos", "contexto": "hipertensa, depende da UBS da Vila Operária", "sentimento": "desgastada"},
        "blocks": [
            [("Eu sou cuidadora de idosos, moro na Vila Operária. Cuido da saúde dos outros e esqueço da minha, essa é a verdade.", None)],
            [("Fui na UBS em setembro porque tava com pressão alta. Cheguei às cinco da manhã pra pegar ficha.", "Cinco da manhã pra pegar ficha. Como foi essa madrugada?"),
             ("Frio, fila enorme na calçada, gente idosa em pé. Abriram às sete e as fichas acabaram em dez minutos, eu fui a décima oitava.", None)],
            [("Consegui, mas o médico atendeu rapidinho, nem olhou direito pra mim. Passou remédio e mandou voltar em três meses.", None)],
            [("Já desisti sim. Quando é pra marcar exame, o encaminhamento demora tanto que eu acabo pagando particular.", "Você acaba pagando particular. Como isso pesa pra você?"),
             ("Pesa muito, eu ganho um salário e pouquinho. Um ultrassom particular come quase metade do que eu recebo em uma semana.", None)],
            [("Marcar consulta por telefone ou WhatsApp, sem precisar de madrugar na fila. E mais médico, porque só tem um pra bairro inteiro.", None)],
        ],
    },
    {
        "n": 7, "script": S, "participant": "demo-p06", "when": (8, 14, 0),
        "profile": {"ocupacao": "atendente de padaria", "contexto": "mãe de bebê de 8 meses", "sentimento": "culpada por não conseguir levar a filha"},
        "blocks": [
            [("Sou mãe de primeira viagem, minha filha tem 8 meses. Moro em Sarandi e trabalho como atendente de padaria.", None)],
            [("Levei ela pra vacina semana passada. A UBS é perto de casa então foi tranquilo.", "Foi tranquilo por ser perto de casa. E como foi o atendimento dentro da UBS?"),
             ("A enfermeira foi ótima, muito atenciosa, explicou tudo. O problema foi esperar quase duas horas com bebê no colo e sem cadeira pra sentar.", None)],
            [("Pra agendar tem que ir lá pessoalmente. Liguei várias vezes e ninguém atende o telefone.", None)],
            [("Já. Uma vez ela tava com tosse e eu desisti de ir porque tinha que pedir folga e perder o dia.", "Você desistiu porque teria que perder o dia de trabalho. Como foi decidir isso?"),
             ("Fiquei com peso na consciência. Levei ela na farmácia, a moça indicou um xarope. Depois piorou e aí fui pro pronto atendimento.", None)],
            [("Horário até de noite ou no sábado, pra quem trabalha. E mais cadeiras na sala de espera, parece detalhe mas faz diferença.", None)],
        ],
    },
    {
        "n": 8, "script": S, "participant": "demo-p07", "when": (10, 8, 45),
        "profile": {"ocupacao": "lavrador aposentado", "contexto": "esposa diabética, UBS a 15 km do sítio"},
        "blocks": [
            [("Eu sou lavrador aposentado, moro no sítio faz quarenta anos. Minha esposa é diabética e a gente depende da UBS pra pegar a insulina.", None)],
            [("A última vez foi mês passado, a agente de saúde passou lá em casa e avisou que o remédio chegou.", "A agente de saúde avisou que o remédio chegou. E como foi buscar?"),
             ("Fomos de carona com o genro, a UBS é a quinze quilômetros. Quando chegamos faltava a insulina, mandaram voltar na semana seguinte.", "Faltava a insulina e mandaram voltar. O que vocês fizeram nesse meio tempo?")],
        ],
    },
    {
        "n": 9, "script": S, "participant": None, "when": (11, 16, 30),
        "profile": {"ocupacao": "estudante de curso técnico", "contexto": "mora com a avó"},
        "blocks": [
            [("Tenho 19 anos, faço curso técnico e moro com minha avó no Jardim Liberdade. Quase não vou ao médico, só quando tá feio.", None)],
            [],
        ],
    },
    {
        "n": 10, "script": A, "participant": "demo-p08", "when": (13, 21, 10),
        "profile": {"ocupacao": "entregador de moto", "contexto": "dois anos e meio no aplicativo de entregas", "sentimento": "exausto e sem proteção"},
        "blocks": [
            [("Sou entregador de moto faz dois anos e meio. Comecei porque perdi o emprego numa loja e precisava de dinheiro rápido.", None)],
            [("Ontem comecei às 11h e parei às 23h. Rodei mais de cem quilômetros e tirei uns cento e vinte reais, descontando a gasolina.", "Doze horas rodando. E nesse tempo, como foi o seu corpo e a sua cabeça?"),
             ("Cansaço puro. Almocei um salgado na moto, sem hora pra parar, porque se eu paro o aplicativo para de mandar pedido bom.", None)],
            [("O ganho cai todo mês, a taxa por entrega diminuiu e a gasolina subiu. E se eu caio da moto não tenho nada, nenhum direito.", "Se você cai da moto não tem nada. Isso já aconteceu com você?"),
             ("Aconteceu em agosto, escorreguei na chuva. Fiquei quinze dias sem trabalhar e ninguém me pagou nada, só tive que arcar com o conserto da moto.", None)],
            [("Queria que mostrassem como calculam o valor da entrega. Hoje é uma caixa preta, a gente não sabe por que um dia paga bem e no outro paga mal.", None)],
        ],
    },
    {
        "n": 11, "script": A, "participant": "demo-p09", "when": (15, 13, 25),
        "profile": {"ocupacao": "motorista de aplicativo", "contexto": "mãe solo, dois filhos, trabalha à noite", "sentimento": "com medo, mas precisa do ganho"},
        "blocks": [
            [("Dirijo pra aplicativo há quase quatro anos, fiz isso depois do divórcio pra sustentar meus dois filhos. Moro em Sarandi.", None)],
            [("Ontem foi puxado. Saí às seis da tarde, fiz corrida até as duas da manhã. Um passageiro bêbado quase vomitou no carro.", "Corrida até as duas da manhã. Como é trabalhar nesse horário sendo mulher?"),
             ("Dá medo. Eu evito algumas regiões e já deixei de aceitar corrida por isso, mas aí a minha nota cai e o aplicativo me pune.", None)],
            [("Acho que a segurança, e também o ganho que não é fixo. Se o carro quebra, o prejuízo é meu.", None)],
            [("Queria poder recusar corrida sem ser punida. E um suporte de verdade, com gente, porque hoje só tem robô respondendo.", None)],
        ],
    },
    {
        "n": 12, "script": A, "participant": "demo-p10", "when": (17, 20, 0),
        "profile": {"ocupacao": "entregador de bicicleta", "contexto": "vai de Paiçandu a Maringá todos os dias"},
        "blocks": [
            [("Faço entrega de bicicleta, tô há seis meses. Moro em Paiçandu e vou pra Maringá todo dia.", None)],
            [("Hoje comecei às 17h. Já fiz uns oito pedidos.", "Oito pedidos até agora. Como está sendo o dia?")],
        ],
    },
    {
        "n": 13, "script": G, "participant": "demo-p04", "when": (18, 11, 0),
        "profile": {"ocupacao": "trabalhadora rural (colheita)", "contexto": "mãe de três filhos, mora no sítio", "sentimento": "sobrecarregada"},
        "blocks": [
            [("Sou a Cris, trabalho na colheita e cuido dos meus três filhos. Meu dia começa às quatro da manhã.", None)],
            [("Acho que é a falta de tempo. Na última vez que precisei resolver um documento na cidade perdi o dia inteiro.", "Perdeu o dia inteiro. Como foi esse dia?"),
             ("Fui pra fila do cartório, depois a fila do banco. Voltei de noite e ainda tinha janta pra fazer.", None)],
            [("Distância. Tudo é longe e eu dependo dos outros pra me levar.", None)],
            [("Ter as coisas mais perto, um posto de atendimento no distrito mesmo.", "Um posto no distrito. O que ele resolveria pra você, por exemplo?"),
             ("Evitava perder o dia de trabalho. Eu perco o pagamento da diária quando falto, sabe.", None)],
        ],
    },
    {
        "n": 14, "script": G, "participant": "demo-p10", "when": (20, 15, 40),
        "profile": {"ocupacao": "operador de mercado e estudante", "contexto": "jovem da periferia, concilia trabalho e curso", "sentimento": "invisibilizado"},
        "blocks": [
            [("Tenho 21 anos, moro em Paiçandu e trabalho de dia no mercado. À noite faço um curso de informática.", None)],
            [("Acho que aparece na hora de conciliar tudo. Ontem saí do mercado às 18h e cheguei atrasado no curso.", "Chegou atrasado no curso. O que aconteceu?"),
             ("O ônibus demorou, aí perdi a primeira aula. A professora é legal mas o conteúdo foi corrido.", None)],
            [("Sinto que ninguém ouve a gente jovem da periferia. Parece que só aparece quando é pra falar de problema.", None)],
            [("Mais oportunidade de curso gratuito perto de casa e alguém pra ouvir de verdade.", "Alguém pra ouvir de verdade. Como você imagina isso?"),
             ("Um espaço no bairro, tipo uma roda de conversa mesmo, onde a prefeitura escutasse o que a gente precisa.", None)],
        ],
    },
]

# (session_id, resumo, [(tema, pontos, [(session_id, citação literal)])], lacunas)
_SESSAO = [
    (
        "demo-s01",
        "Diarista de Maringá enfrenta espera longa em ponto sem cobertura e gasta boa parte da renda com passagem. A falta de horários já a fez perder diária e atrasar o socorro ao filho doente.",
        [
            ("Espera longa e incerteza dos horários", ["Pontos sem cobertura", "Aplicativo de horários não é confiável"],
             [("demo-s01", "Esperei o ônibus quarenta minutos no ponto, que não tem cobertura"), ("demo-s01", "se eu chego atrasada a patroa desconta")]),
            ("Peso da passagem no orçamento", ["Tarifa de R$ 5,10", "Cerca de uma diária por semana vai só em transporte"],
             [("demo-s01", "É quase uma diária por semana só pra ir trabalhar")]),
            ("Mobilidade e saúde da família", ["Ônibus do bairro passa de hora em hora"],
             [("demo-s01", "fui a pé até a avenida com ele no colo")]),
        ],
        ["Não foi explorado se existem linhas alternativas no bairro."],
    ),
    (
        "demo-s02",
        "Estudante que mora em Sarandi depende do último ônibus das 23h10 e sente medo ao esperar sozinho à noite. Já perdeu prova por falha do transporte.",
        [
            ("Horários noturnos insuficientes", ["Último ônibus às 23h10", "Espera de mais de uma hora no terminal"],
             [("demo-s02", "o último ônibus pra Sarandi sai 23h10")]),
            ("Sensação de insegurança", ["Terminal vazio", "Dependência de familiar para buscar"],
             [("demo-s02", "Fiquei no terminal, quase vazio, com um pouco de medo")]),
            ("Impacto nos estudos", ["Falta em prova por ônibus quebrado", "Demanda por passe estudantil intermunicipal"],
             [("demo-s02", "o professor não deixou entrar"), ("demo-s02", "um passe estudantil que funcione também nas linhas intermunicipais")]),
        ],
        ["Não ficou claro quanto ele gasta por mês com transporte."],
    ),
    (
        "demo-s03",
        "Idoso de Paiçandu usa o ônibus quase só para ir ao médico e enfrenta degraus altos, motoristas apressados e medo de ir sozinho. Já deixou de ir a consultas.",
        [
            ("Acessibilidade para idosos", ["Degraus altos", "Motorista arranca antes de a pessoa sentar"],
             [("demo-s03", "Ninguém me ajudou, só uma moça que me segurou"), ("demo-s03", "pra gente velho é difícil")]),
            ("Consultas perdidas", ["Medo de ir sozinho", "Remarcação leva meses"],
             [("demo-s03", "Remarcar demora meses, aí a dor piora")]),
        ],
        ["Falta saber se ele conhece o benefício de gratuidade para idosos."],
    ),
    (
        "demo-s05",
        "Vendedora de marmitas se sente mal recebida no ônibus por levar mercadoria e perde encomendas grandes por não conseguir transportá-las.",
        [
            ("Constrangimento ao carregar mercadoria", ["Reclamação do motorista pelo volume"],
             [("demo-s05", "Parece que a gente que carrega peso não é bem-vinda no ônibus")]),
            ("Perda de renda", ["Encomendas grandes recusadas", "Tarifa pesa para quem usa o ônibus como trabalho"],
             [("demo-s05", "deixei de buscar encomenda grande porque não dava pra levar de ônibus"), ("demo-s05", "uma tarifa menor pra quem usa pra trabalhar")]),
        ],
        ["Entrevista sem participante identificado; faltam dados de região."],
    ),
    (
        "demo-s06",
        "Cuidadora de idosos enfrenta fila de madrugada para conseguir ficha, consulta rápida e demora em exames, o que a leva a pagar particular com renda apertada.",
        [
            ("Acesso por ficha e fila de madrugada", ["Fichas acabam em minutos", "Pessoas idosas esperando em pé"],
             [("demo-s06", "Cheguei às cinco da manhã pra pegar ficha"), ("demo-s06", "as fichas acabaram em dez minutos")]),
            ("Qualidade percebida da consulta", ["Atendimento rápido, sem escuta"],
             [("demo-s06", "nem olhou direito pra mim")]),
            ("Custo de recorrer ao particular", ["Encaminhamento de exames demora", "Ultrassom particular pesa no orçamento"],
             [("demo-s06", "o encaminhamento demora tanto que eu acabo pagando particular"), ("demo-s06", "Marcar consulta por telefone ou WhatsApp, sem precisar de madrugar na fila")]),
        ],
        ["Não foi perguntado qual UBS específica ela frequenta."],
    ),
    (
        "demo-s07",
        "Mãe de bebê elogia a enfermeira, mas relata espera longa sem cadeiras, agendamento só presencial e dificuldade de faltar ao trabalho para levar a filha.",
        [
            ("Espera e estrutura da UBS", ["Quase duas horas de espera", "Falta de cadeiras"],
             [("demo-s07", "esperar quase duas horas com bebê no colo e sem cadeira pra sentar")]),
            ("Agendamento inacessível", ["Telefone não é atendido", "Agendamento só presencial"],
             [("demo-s07", "Liguei várias vezes e ninguém atende o telefone")]),
            ("Horário de funcionamento incompatível com o trabalho", ["Desistência por perder o dia"],
             [("demo-s07", "tinha que pedir folga e perder o dia"), ("demo-s07", "Horário até de noite ou no sábado, pra quem trabalha")]),
        ],
        ["Não se explorou a experiência no pronto atendimento."],
    ),
    (
        "demo-s10",
        "Entregador de moto trabalha jornadas de doze horas por ganho decrescente, sem direitos em caso de acidente, e pede transparência no cálculo do valor das entregas.",
        [
            ("Jornada longa e pressão do aplicativo", ["Sem pausas para refeição"],
             [("demo-s10", "se eu paro o aplicativo para de mandar pedido bom")]),
            ("Ausência de proteção", ["Acidente sem auxílio", "Custo do conserto por conta própria"],
             [("demo-s10", "se eu caio da moto não tenho nada, nenhum direito"), ("demo-s10", "Fiquei quinze dias sem trabalhar e ninguém me pagou nada")]),
            ("Falta de transparência nos valores", ["Pagamento imprevisível"],
             [("demo-s10", "Hoje é uma caixa preta")]),
        ],
        ["Não foi explorada a relação com outros entregadores."],
    ),
    (
        "demo-s11",
        "Motorista de aplicativo e mãe solo sente medo à noite, evita regiões e teme ser punida pela nota ao recusar corridas. Pede suporte humano.",
        [
            ("Segurança no trabalho noturno", ["Evita regiões perigosas"],
             [("demo-s11", "Dá medo. Eu evito algumas regiões")]),
            ("Punição por recusar corridas", ["Nota reduzida pela plataforma"],
             [("demo-s11", "a minha nota cai e o aplicativo me pune")]),
            ("Risco financeiro e suporte", ["Custos do carro recaem sobre ela", "Suporte automatizado"],
             [("demo-s11", "Se o carro quebra, o prejuízo é meu"), ("demo-s11", "hoje só tem robô respondendo")]),
        ],
        ["Falta saber quanto ela ganha líquido por mês."],
    ),
    (
        "demo-s13",
        "Trabalhadora rural com três filhos perde dias inteiros para resolver burocracias na cidade por causa da distância e pede um posto de atendimento no distrito.",
        [
            ("Rotina sobrecarregada", ["Dia começa às quatro da manhã"],
             [("demo-s13", "Meu dia começa às quatro da manhã")]),
            ("Distância dos serviços", ["Depende de outros para se locomover"],
             [("demo-s13", "Tudo é longe e eu dependo dos outros pra me levar")]),
            ("Perda de renda por deslocamento", ["Diária perdida quando falta"],
             [("demo-s13", "um posto de atendimento no distrito mesmo"), ("demo-s13", "Eu perco o pagamento da diária quando falto")]),
        ],
        ["Não foi perguntado sobre apoio da família ou da comunidade."],
    ),
    (
        "demo-s14",
        "Jovem de Paiçandu que trabalha e estuda sente que a juventude da periferia não é ouvida e pede cursos gratuitos e espaços de escuta no bairro.",
        [
            ("Sentir-se invisível", ["Só é lembrado quando é problema"],
             [("demo-s14", "ninguém ouve a gente jovem da periferia")]),
            ("Falta de oportunidades próximas", ["Cursos gratuitos perto de casa"],
             [("demo-s14", "Mais oportunidade de curso gratuito perto de casa")]),
            ("Participação na decisão pública", ["Rodas de conversa no bairro"],
             [("demo-s14", "onde a prefeitura escutasse o que a gente precisa")]),
        ],
        ["Não ficou claro se ele já participou de algum conselho ou grupo do bairro."],
    ),
]

_ROTEIRO = (
    T,
    "Nas quatro entrevistas concluídas sobre transporte na periferia, a espera longa, o custo da passagem e a falta de horários noturnos limitam trabalho, estudo e acesso à saúde. Idosos e trabalhadoras informais relatam, além disso, falta de acolhimento no ônibus.",
    [
        ("Horários insuficientes e espera sem estrutura", ["Pontos sem cobertura", "Último ônibus muito cedo"],
         [("demo-s01", "Esperei o ônibus quarenta minutos no ponto, que não tem cobertura"), ("demo-s02", "o último ônibus pra Sarandi sai 23h10")]),
        ("Transporte caro para quem vive de renda pequena", ["Passagem consome parte relevante do ganho"],
         [("demo-s01", "É quase uma diária por semana só pra ir trabalhar"), ("demo-s05", "uma tarifa menor pra quem usa pra trabalhar")]),
        ("Falta de acolhimento e acessibilidade", ["Idosos com dificuldade para embarcar", "Constrangimento com bagagem"],
         [("demo-s03", "pra gente velho é difícil"), ("demo-s05", "Parece que a gente que carrega peso não é bem-vinda no ônibus")]),
        ("Insegurança à noite", ["Terminais vazios e pontos escuros"],
         [("demo-s02", "Fiquei no terminal, quase vazio, com um pouco de medo")]),
    ],
    [
        "Nenhuma entrevista de pessoa com deficiência.",
        "A sessão da moradora rural ainda está em andamento e não entrou na síntese.",
    ],
)

SYNTHESIS_SPECS = {"sessao": _SESSAO, "roteiro": _ROTEIRO}
