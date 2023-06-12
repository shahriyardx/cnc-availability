/*
  Warnings:

  - You are about to drop the `lineups` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropTable
DROP TABLE "lineups";

-- CreateTable
CREATE TABLE "PlayerLineup" (
    "id" TEXT NOT NULL,
    "member_id" BIGINT NOT NULL,
    "week" INTEGER NOT NULL,
    "year" INTEGER NOT NULL,
    "lineupId" TEXT NOT NULL,

    CONSTRAINT "PlayerLineup_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "PlayerLineup" ADD CONSTRAINT "PlayerLineup_lineupId_fkey" FOREIGN KEY ("lineupId") REFERENCES "Lineup"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
