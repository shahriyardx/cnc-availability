-- CreateTable
CREATE TABLE "Availability" (
    "id" TEXT NOT NULL,
    "member_id" BIGINT NOT NULL,
    "games" INTEGER NOT NULL,

    CONSTRAINT "Availability_pkey" PRIMARY KEY ("id")
);
