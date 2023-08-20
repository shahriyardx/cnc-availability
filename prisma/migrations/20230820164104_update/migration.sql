/*
  Warnings:

  - You are about to drop the column `center` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `goalie` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `left_defense` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `left_wing` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `message_id_cnc` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `message_id_team` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `right_defense` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `right_wing` on the `Lineup` table. All the data in the column will be lost.
  - You are about to drop the column `lineupId` on the `PlayerLineup` table. All the data in the column will be lost.
  - Added the required column `data` to the `Lineup` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "PlayerLineup" DROP CONSTRAINT "PlayerLineup_lineupId_fkey";

-- AlterTable
ALTER TABLE "Lineup" DROP COLUMN "center",
DROP COLUMN "goalie",
DROP COLUMN "left_defense",
DROP COLUMN "left_wing",
DROP COLUMN "message_id_cnc",
DROP COLUMN "message_id_team",
DROP COLUMN "right_defense",
DROP COLUMN "right_wing",
ADD COLUMN     "data" TEXT NOT NULL;

-- AlterTable
ALTER TABLE "PlayerLineup" DROP COLUMN "lineupId";
