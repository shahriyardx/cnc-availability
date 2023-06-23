import os

mode = os.getenv("MODE")
inactive_roles_prod = [
    905467263388377149,
    905467040272375829,
    905468012184895500,
    905468259439108136,
    905466998463541269,
    905467992345837588,
    905467926931447839,
    905467022404644934,
    905467971412066325,
    893538572387368970,
    905467953179406378,
    905466970210721872,
    905466950723989535,
    905466932831080478,
    905466913050751007,
    905466897108185159,
    905466879320141824,
    905466860634509393,
    905466840178901012,
    905466810642616381,
    905466788207263754,
    905466770230505564,
    905466751867813959,
    905466640811040878,
    905467391566286878,
    905467346645319782,
    871247736031293460,
    850498185674752030,
    946813185036529696,
    964040349213421578,
    950202853560049694,
    958094227429003274,
    950202255515222107,
    958094311784853516,
    950201421171671040,
    950198899778396170,
    950199086114566204,
    950198484307419207,
    950198462446731264,
    950198317588037662,
    950198118538952744,
    950197435291009074,
    950197270941401179,
    950197013683773512,
    972144661248487454,
    972144485104517130,
    898864179136573440,
    898863372685172786,
    898863856225509397,
    898862960183754772,
    866052948257144853,
    898862657464045568,
    898862294056984587,
    866052308063223818,
    866054888790163497,
    898861751456657439,
    866053937210458133,
    898861333041270785,
    898860897848684565,
    898860465818574859,
    898818861342797834,
    898809034554093598,
    898807845506650112,
    898806604374372422,
    898806593431408640,
    898806181995364353,
    898805664149815296,
    898805085163892787,
    898804639280033842,
    898803861395996672,
    894118502233952258,
    898790672251879424,
    866060496331472946,
    898790224497377340,
    898785953139798037,
    898785620984475659,
    898785094490263622,
    898783553515577344,
    863516927388549151,
    951479776349130785,
    851509481803087922,
    863516734944968704,
]
inactive_roles_dev = [1080891453833744466]
support_server_id = 1055597639028183080 if "dev" in mode else 831166408888942623
inactive_roles = inactive_roles_dev if "dev" in mode else inactive_roles_prod
ir_channel = 1112948119353700363 if "dev" in mode else 1105261762435096677
inactive_channel = 1112948150869704775 if "dev" in mode else 1105262064982827129