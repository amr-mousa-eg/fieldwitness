export interface TeamMember {
  id: string;
  nameEn: string;
  nameAr: string;
  roleEn: string;
  roleAr: string;
  affiliationEn: string;
  affiliationAr: string;
  email: string;
  initials: string;
  /** Optional photo path inside app/public/ (e.g. "./team/amr.jpg"). When null, renders crisp initials avatar. */
  photoUrl: string | null;
}

export const HOME_LINKS = {
  repoUrl: "https://github.com/amr-mousa-eg/fieldwitness",
  paperPdfUrl: "./paper/FieldWitness_Research_Paper.pdf",
  paperDocxUrl: "./paper/FieldWitness_Research_Paper.docx",
  /** Set to a public YouTube embed URL or MP4 URL once the 2-minute walkthrough video is recorded. */
  demoVideoUrl: null as string | null,
};

export const TEAM_MEMBERS: TeamMember[] = [
  {
    id: "amr",
    nameEn: "Amr Mousa Abdel-Haii",
    nameAr: "عمرو موسى عبد الحي",
    roleEn: "High School Student",
    roleAr: "طالب ثانوي",
    affiliationEn: "Assiut STEM School · Assiut, Egypt",
    affiliationAr: "مدرسة المتفوقين للعلوم والتكنولوجيا بأسيوط · أسيوط، مصر",
    email: "amr.1424040@stemassiut.moe.edu.eg",
    initials: "AM",
    photoUrl: null,
  },
  {
    id: "mohamed",
    nameEn: "Mohamed Abdallah Mosbah",
    nameAr: "محمد عبد الله مصباح",
    roleEn: "High School Student",
    roleAr: "طالب ثانوي",
    affiliationEn: "Assiut STEM School · Assiut, Egypt",
    affiliationAr: "مدرسة المتفوقين للعلوم والتكنولوجيا بأسيوط · أسيوط، مصر",
    email: "Mohamad.1424047@stemassiut.moe.edu.eg",
    initials: "MA",
    photoUrl: null,
  },
  {
    id: "muhammed",
    nameEn: "Muhammed Mahmoud Mohamed",
    nameAr: "محمد محمود محمد",
    roleEn: "High School Student",
    roleAr: "طالب ثانوي",
    affiliationEn: "Assiut STEM School · Assiut, Egypt",
    affiliationAr: "مدرسة المتفوقين للعلوم والتكنولوجيا بأسيوط · أسيوط، مصر",
    email: "Muhammed.1424051@stemassiut.moe.edu.eg",
    initials: "MM",
    photoUrl: null,
  },
  {
    id: "youssef",
    nameEn: "Youssef Ahmed Ragaa",
    nameAr: "يوسف أحمد رجاء",
    roleEn: "High School Student",
    roleAr: "طالب ثانوي",
    affiliationEn: "Assiut STEM School · Assiut, Egypt",
    affiliationAr: "مدرسة المتفوقين للعلوم والتكنولوجيا بأسيوط · أسيوط، مصر",
    email: "Youssef.1424064@stemassiut.moe.edu.eg",
    initials: "YA",
    photoUrl: null,
  },
  {
    id: "abdelrahman",
    nameEn: "Abdelrahman Ibrahim Abdelrahman",
    nameAr: "عبد الرحمن إبراهيم عبد الرحمن",
    roleEn: "High School Student",
    roleAr: "طالب ثانوي",
    affiliationEn: "Assiut STEM School · Assiut, Egypt",
    affiliationAr: "مدرسة المتفوقين للعلوم والتكنولوجيا بأسيوط · أسيوط، مصر",
    email: "Abdel.1424033@stemassiut.moe.edu.eg",
    initials: "AI",
    photoUrl: null,
  },
];
