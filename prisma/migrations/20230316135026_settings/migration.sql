-- CreateTable
CREATE TABLE "Settings" (
    "id" TEXT NOT NULL,
    "can_submit_lineups" BOOLEAN NOT NULL DEFAULT true,
    "can_edit_lineups" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "Settings_pkey" PRIMARY KEY ("id")
);
