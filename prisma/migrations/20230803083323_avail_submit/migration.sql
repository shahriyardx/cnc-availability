-- CreateTable
CREATE TABLE "AvailabilitySubmitted" (
    "id" TEXT NOT NULL,
    "member_id" BIGINT NOT NULL,
    "day" TEXT NOT NULL,
    "time" TEXT NOT NULL,
    "week" INTEGER NOT NULL,

    CONSTRAINT "AvailabilitySubmitted_pkey" PRIMARY KEY ("id")
);
