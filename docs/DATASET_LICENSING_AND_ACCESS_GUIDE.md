# DATASET LICENSING, ACCESS PROCEDURES, AND COMPLIANCE GUIDE
**Project Title:** Development and Validation of an rPPG-Based System for Non-Contact Vital Sign Monitoring  
**Document Code:** BME-FYP-ACCESS-001  
**Compliance Mandate:** Zero Unauthorized Scraping — Respect All Institutional EULAs  

---

## 1. Compliance Statement & Research Ethics

In strict compliance with the Master Project Specification:
* **No credentials, access barriers, or institutional verification portals are bypassed.**
* Datasets that require formal data use agreements (DUAs), Non-Disclosure Agreements (NDAs), or faculty supervisor signatures must be obtained through their authorized channels.
* Below are the official access procedures, contact points, and application templates for each repository.

---

## 2. Dataset-by-Dataset Access Protocols

### 2.1 MMPD (Multi-Domain Mobile Video Physiology Dataset)
* **Access Level:** **Public Open Access (No Application Required)**
* **License:** MIT License (Academic & Commercial Permitted)
* **Official Repository:** `https://github.com/McDuff-App/MMPD`
* **Direct Acquisition Method:**
  Can be cloned directly via Google Colab into Google Drive:
  ```bash
  git clone --depth 1 https://github.com/McDuff-App/MMPD.git "/content/drive/MyDrive/RPPG_FYP/01_RAW_DATASETS/MMPD"
  ```

---

### 2.2 UBFC-rPPG (University of Bourgogne Franche-Comté)
* **Access Level:** **Academic Research Access upon Request**
* **License:** Creative Commons Non-Commercial Academic Use Agreement
* **Official Portal:** `https://sites.google.com/view/ybobbia/ubfc-rppg`
* **Application Procedure:**
  1. Visit the official project webpage hosted by Yannick Bobbia / Univ Bourgogne.
  2. Fill out the academic request form with your institutional university email address (`.edu` or institutional domain).
  3. Specify: Final Year Project in Biomedical Engineering, supervisor's name, and research objectives.
  4. Upon verification, the research team provides an authorized Google Drive access link.
  5. The authorized link can then be downloaded directly into `RPPG_FYP/01_RAW_DATASETS/UBFC-rPPG/` via Google Colab without downloading to your local PC.

---

### 2.3 PURE (Pulse Rate Estimation from Facial Videos)
* **Access Level:** **Restricted Academic EULA Required**
* **License:** TU Ilmenau Academic Research License
* **Official Source:** `https://www.tu-ilmenau.de/en/applied-media-systems-group/research/databases/pure`
* **Application Procedure:**
  1. Contact the Applied Media Systems Group at TU Ilmenau via email: `ams-database@tu-ilmenau.de`.
  2. Subject: `PURE Database Access Request - Undergraduate FYP [University Name]`.
  3. Include the signed End User License Agreement (EULA) downloaded from their portal.
  4. The agreement must state that all facial video frames will remain strictly protected and confidential.
  5. The lab will issue unique SFTP or HTTPS credentials for cloud acquisition.

---

### 2.4 COHFACE (Idiap Research Institute)
* **Access Level:** **Online Registration & Click-Through EULA**
* **License:** Idiap Non-Commercial Research License
* **Official Portal:** `https://www.idiap.ch/en/dataset/cohface`
* **Application Procedure:**
  1. Navigate to the Idiap Dataset portal and click **Register for an Account**.
  2. Register using your institutional university email.
  3. Accept the Idiap Non-Commercial Research License terms.
  4. Verify your email and login.
  5. Under the **COHFACE** section, obtain your personal API token or direct download URLs.
  6. In Google Colab, input the token into Colab Secrets to download the archives directly into `RPPG_FYP/01_RAW_DATASETS/COHFACE/`.

---

### 2.5 VIPL-HR (Visual-Optical Physiological Laboratory)
* **Access Level:** **Signed Institutional Application Form Required**
* **License:** Chinese Academy of Sciences Academic License
* **Official Portal:** `http://vipl.ict.ac.cn/resources/datasets`
* **Application Procedure:**
  1. Download the VIPL-HR Dataset Release Agreement from the VIPL ICT website.
  2. Complete the form with project title, primary investigator (faculty advisor), and university affiliation.
  3. Have your university department chair or faculty supervisor sign and stamp the agreement.
  4. Scan and email the completed PDF to: `vipl_hr@ict.ac.cn`.
  5. Approval is typically granted within 2 to 4 weeks with Baidu Netdisk or direct HTTP credentials.

---

### 2.6 BP4D+ (Binghamton-Pittsburgh 4D Multimodal Corpus)
* **Access Level:** **Institutional Review Board (IRB) / Faculty PI Sign-Off**
* **License:** Binghamton University Research Agreement
* **Official Portal:** `http://www.cs.binghamton.edu/~lijun/Research/BP4D+/index.html`
* **Application Procedure:**
  1. Review the BP4D+ Data Release Agreement.
  2. Because the dataset contains high-resolution 3D facial geometry and synchronized clinical hemodynamics (continuous blood pressure), the agreement must be signed by a tenured university faculty member.
  3. Submit the signed application to Prof. Lijun Yin at Binghamton University (`lijun@cs.binghamton.edu`).
  4. Upon approval, authorized cloud download credentials will be provided.

---

## 3. Academic Request Email Template

Below is a standard template for requesting access to restricted academic datasets:

```
Subject: Academic Data Use Agreement Request: [Dataset Name] for Biomedical Engineering Research

Dear [Dataset Administrator / Research Team],

I am writing to formally request access to the [Dataset Name] dataset for academic research purposes in connection with my Final Year Project (FYP) entitled:
"Development and Validation of an rPPG-Based System for Non-Contact Vital Sign Monitoring"
at the Department of Biomedical Engineering, [University Name].

Project Details:
- Student Researcher: [Your Name] ([Your University Email])
- Faculty Advisor / Supervisor: [Supervisor Name], [Title / Department]
- Institution: [University Name, Country]
- Research Purpose: Evaluating remote photoplethysmography (rPPG) digital signal processing and deep-learning architectures against synchronized clinical ground-truth signals.
- Security Protocol: All dataset archives will be stored exclusively in a secure, access-controlled institutional cloud repository with strict pseudonymization. No video frames will be redistributed or published publicly without explicit authorization.

I have reviewed and attached the completed and signed [Dataset Name] End User License Agreement (EULA).

Thank you very much for your time and for supporting open biomedical engineering research.

Sincerely,

[Your Name]
Undergraduate Researcher, Biomedical Engineering
[University Name]
```

