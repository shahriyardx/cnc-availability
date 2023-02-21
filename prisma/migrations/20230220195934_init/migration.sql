-- CreateTable
CREATE TABLE "Lineup" (
    "id" TEXT NOT NULL,
    "team" TEXT NOT NULL,
    "day" TEXT NOT NULL,
    "time" TEXT NOT NULL,
    "left_wing" BIGINT NOT NULL,
    "right_wing" BIGINT NOT NULL,
    "left_defense" BIGINT NOT NULL,
    "right_defense" BIGINT NOT NULL,
    "center" BIGINT NOT NULL,
    "goalie" BIGINT NOT NULL,

    CONSTRAINT "Lineup_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "lineups" (
    "id" TEXT NOT NULL,
    "member_id" BIGINT NOT NULL,
    "week" INTEGER NOT NULL,
    "year" INTEGER NOT NULL,

    CONSTRAINT "lineups_pkey" PRIMARY KEY ("id")
);
