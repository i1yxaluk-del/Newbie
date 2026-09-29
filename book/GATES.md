# Gates: MSPShield Academy MD — этап 0

Scope: сначала спроектировать связное оглавление и стандарт написания учебника; главы пока не писать.

- [ ] G1: оглавление ведёт Junior-сисадмина от базовых моделей к самостоятельному развёртыванию и эксплуатации
  CHECK: python3 /data/MSPShield_Academy_MD/verify_stage0.py structure
  EXPECT: STRUCTURE_OK
  EVIDENCE: pending

- [ ] G2: техническая программа учитывает актуальный main 89249e43 и уроки миграции 28.09
  CHECK: python3 /data/MSPShield_Academy_MD/verify_stage0.py repository
  EXPECT: REPOSITORY_OK
  EVIDENCE: pending

- [ ] G3: экономика и продажи изучаются после технической базы и завершаются самостоятельной моделью MSP
  CHECK: python3 /data/MSPShield_Academy_MD/verify_stage0.py business
  EXPECT: BUSINESS_OK
  EVIDENCE: pending

- [ ] G4: методика исключает словарные главы, повторяющийся boilerplate и определения через неопределённые слова
  CHECK: python3 /data/MSPShield_Academy_MD/verify_stage0.py pedagogy
  EXPECT: PEDAGOGY_OK
  EVIDENCE: pending

- [ ] G5: правила контроля фактов отделяют repository fact, external fact, assumption и учебную модель
  CHECK: python3 /data/MSPShield_Academy_MD/verify_stage0.py factuality
  EXPECT: FACTUALITY_OK
  EVIDENCE: pending

- [ ] G6: каждый пункт оглавления содержит prerequisites, содержание, практикум и конкретный итоговый артефакт
  CHECK: python3 /data/MSPShield_Academy_MD/verify_stage0.py chapters
  EXPECT: CHAPTERS_OK
  EVIDENCE: pending
