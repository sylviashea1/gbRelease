import os
import sys
import zipfile
import subprocess
import datetime

#For testing
try:
    working = os.environ['GITHUB_WORKSPACE']
except:
    working = "/home/dan/git/gbRelease"
print("Python WD: " + working)  

#For testing
try:
    changedFiles = os.environ['changes'].strip('][').split(',')
except:
    changedFiles = ['.github/workflows/gbPush.yml', 'sourceData/ARE_ADM1.zip', 'sourceData/QAT_ADM0.zip']

print("Python changedFiles: " + str(changedFiles))


#Check that zip files exist in the request
zips = list(filter(lambda x: x[-4:] == '.zip', changedFiles))

zipFailures = 0
zipSuccess = 0
zipTotal = 0
anyFail = 0

#Load ISOs for later checks
with open(working + "/actions/dta/iso_3166_1_alpha_3.csv") as isoCsv:
    lines = isoCsv.readlines()

validISO = []
for line in lines:
    data = line.split(',')
    validISO.append(data[2])

#Load licenses for later checks
with open(working + "/actions/dta/gbLicenses.csv") as lCsv:
    lines = lCsv.readlines()

validLicense = []
validOpenLicense = []
validAuthLicense = []
validHumLicense = []
for line in lines:
    data = line.split(',')
    validLicense.append(data[0].lower().strip())
    if(str(data[2]).strip() == "Yes"):
        validOpenLicense.append(data[0].lower().strip())
    if(data[3] == "Yes"):
        validAuthLicense.append(data[0].lower().strip())
    if(data[3] == "Yes"):
        validHumLicense.append(data[0].lower().strip())

if(len(zips) > 0):
    print("Modified zip files found.  Checking meta.txt validity.")
    print("")
    zipTotal = zipTotal + 1
    for z in zips:
        req = {}
        opt = {}
        req["year"] = 0
        req["iso"] = 0
        req["bType"] = 0
        req["source"] = 0
        req["releaseType"] = 0
        req["releaseTypeName"] = ""
        req["license"] = 0
        req["licenseName"] = ""
        req["licenseSource"] = 0
        req["dataSource"] = 0
        req["releaseTypeFolder"] = 0

        opt["canonical"] = 0
        opt["licenseImage"] = 0
        opt["licenseNotes"] = 0
        opt["otherNotes"] = 0


        checkFail = 0
        print("")
        print("Downloading: " + z)
        try:
            os.remove(working + "/" + z)
        except:
            pass
        dl = os.system('git lfs pull --include=\"' + z +'\"')
        print("Metadata Check (" + str(zipTotal) + " of " + str(len(zips)) + "): " + z)
        bZip = zipfile.ZipFile(working + "/" + z)
        if("meta.txt" in bZip.namelist()):
            print("")
            print("============================")
            print("Metadata file exists in " + z)

            with zipfile.ZipFile(working + "/" + z) as zF:
                meta = zF.read('meta.txt')
            
            for m in meta.splitlines():
                print("")
                e = m.decode("latin1").split(":")
                if(len(e) > 2):
                    e[1] = e[1] + e[2]
                key = e[0].strip()
                val = e[1].strip()
                
                print("Detected Key / Value: " + key + " / " + val)
                if(("Year" in key) or "year" in key):
                    year = int(float(val))
                    if( (year > 1990) and (year < datetime.datetime.now().year)):
                        print("Valid year " + str(year) + " detected.")
                        req["year"] = 1
                    else:
                        print("CRITICAL ERROR: The year in the meta.txt file is invalid: " + year)
                        print("We expect a value between 1990 and " + datetime.datetime.now().year)
                        checkFail = 1
                
                if("boundary type" in key.lower() and "name" not in key.lower()):
                    #May add other valid types in the future, but for now ADMs only.
                    validTypes = ["ADM0", "ADM1", "ADM2", "ADM3", "ADM4", "ADM5"]
                    if(val.upper().replace(" ","") in validTypes):
                        print("Valid Boundary Type detected: " + val +".")
                        req["bType"] = 1
                    else:
                        print("CRITICAL ERROR: The boundary type in the meta.txt file is invalid: " + val)
                        print("We expect one of: " + str(validTypes))
                        checkFail = 1
                
                if("iso" in key.lower()):
                    if(len(val) != 3):
                        print("CRITICAL ERROR: ISO is invalid - we expect a 3-character ISO code following ISO-3166-1 (Alpha 3).")
                        checkFail = 1
                    if(val not in validISO):
                        print("CRITICAL ERROR: ISO is not on our list of valid ISO-3 codes.  See /actions/dta/iso_3166_1_alpha_3.csv for all valid codes this script checks against.")
                        checkFail = 1
                    else:
                        print("Valid ISO detected: " + val)
                        req["iso"] = 1
                
                if("canonical" in key.lower()):
                    if(len(val.replace(" ","")) > 0):
                        if(val.lower() not in ["na", "nan", "null"]):
                            print("Canonical name detected: " + val)
                            opt["canonical"] = 1
                    else:
                        print("WARN: No canonical name detected.  This field is optional.")
                    
                if("source" in key.lower() and "license" not in key.lower() and "data" not in key.lower()):
                    if(len(val.replace(" ","")) > 0):
                        if(val.lower() not in ["na", "nan", "null"]):
                            print("Source detected: " + val)
                            req["source"] = 1

                if("release type" in key.lower()):
                    if (val.lower() not in ["gbopen", "gbauthoritative", "gbhumanitarian"]):
                        print("Invalid release type detected: " + val)
                        print("We expect one of three values: gbOpen, gbAuthoritative, and gbHumanitarian")
                        checkFail = 1
                    else:
                        if(val.lower() not in z.lower()):
                            req["releaseTypeName"] = val.lower().strip()
                            req["releaseType"] = 1
                            req["releaseTypeFolder"] = 0
                            print("CRITICAL ERROR: The zip file is in the incorrect subdirectory - according to meta.txt you are submitting a " + val + " boundary, but have the zip file in the folder " + z + ".")
                            checkFail = 1
                        else:
                            req["releaseType"] = 1
                            req["releaseTypeName"] = val.lower().strip()
                            req["releaseTypeFolder"] = 1

                if("license" == key.lower()):
                    if(('"' + val.lower().strip() + '"') not in validLicense):
                        print("CRITICAL ERROR: Invalid license detected: " + val)
                        print("We expect one of the licenses in /actions/dta/gbLicenses.csv.  If you believe your license should be included, please open a ticket.")
                        checkFail = 1
                    else:
                        req["license"] = 1
                        req["licenseName"] = val.lower().strip()
                        print("Valid license type detected: " + val)
                        

                if("license notes" in key.lower()):
                    if(len(val.replace(" ","")) > 0):
                        if(val.lower() not in ["na", "nan", "null"]):
                            print("License notes detected: " + val)
                            opt["licenseNotes"] = 1
                    else:
                        print("WARN: No license notes detected.  This field is optional.")

                if("license source" in key.lower()):
                    if(len(val.replace(" ","")) > 0):
                        if(val.lower() not in ["na", "nan", "null"]):
                            print("License source detected: " + val)
                            req["licenseSource"] = 1
                            #Check for a png image of the license source.
                            #Any png or jpg with the name "license" is accepted.
                            licPic = 0
                            try:
                                with zipfile.ZipFile(working + "/" + z) as zFb:
                                    licPic = zFb.read('license.png')
                            except:
                                pass

                            try:
                                with zipfile.ZipFile(working + "/" + z) as zFb:
                                    licPic = zFb.read('license.jpg')
                            except:
                                pass

                            if(licPic != 0):
                                print("License image found.")
                                opt["licenseImage"] = 1
                            else:
                                print("WARN: No license image found.  This is not required.  We check for license.png and license.jpg.")
                        
                        else:
                            print("CRITICAL ERROR: No license source detected.")
                            checkFail = 1


                    else:
                        print("CRITICAL ERROR: No license source detected.")
                        checkFail = 1

                if("link to source data" in key.lower()):
                    if(len(val.replace(" ","")) > 0):
                        if(val.lower() not in ["na", "nan", "null"]):
                            req["dataSource"] = 1
                            print("Data Source Found: " + val)
                                            
                        else:
                            print("CRITICAL ERROR: No license source detected.")
                            checkFail = 1


                    else:
                        print("CRITICAL ERROR: No license source detected.")
                        checkFail = 1

                if("other notes" in key.lower()):
                    if(len(val.replace(" ","")) > 0):
                        if(val.lower() not in ["na", "nan", "null"]):
                            print("Other notes detected: " + val)
                            opt["otherNotes"] = 1
                    else:
                        print("WARN: No other notes detected.  This field is optional.")


            if((req["license"] == 1) and (req["releaseType"] == 1)):
                print("")
                print("Both a license and release type are defined.  Checking for compatability.")
                if(req["releaseTypeName"] == "gbopen"):
                    if(('"' + req["licenseName"] + '"') in validOpenLicense):
                        print("License type is a valid license for the gbOpen product.")
                    else:
                        print("CRITICAL ERROR: The license you have specified is not valid for the gbOpen product.")
                        checkFail = 1
                
                if(req["releaseTypeName"] == "gbauthoritative"):
                    if(('"' + req["licenseName"] + '"') in validAuthLicense): 
                        print("License type is a valid license for the gbAuthoritative product.")
                    else:
                        print("CRITICAL ERROR: The license you have specified is not valid for the gbAuthoritative product.")
                        checkFail = 1

                if(req["releaseTypeName"] == "gbhumanitarian"):
                    if(('"' + req["licenseName"] + '"') in validHumLicense): 
                        print("License type is a valid license for the gbHumanitarian product.")
                    else:
                        print("CRITICAL ERROR: The license you have specified is not valid for the gbHumanitarian product.")
                        checkFail = 1





            if(req["source"] == 0):
                print("CRITICAL ERROR: No data source was provided in the metadata.")
                checkFail = 1

                    

            print("")
            print("Metadata checks complete for " + z)
            print("")
            print("----------------------------")
            print("      OPTIONAL TESTS        ")
            print("----------------------------")
            for i in opt:
                if(opt[i] == 1 or len(str(opt[i]))>1):
                    print('%-20s%-12s' % (i, "PASSED"))
                else:
                    print('%-20s%-12s' % (i, "FAILED"))
            print("")
            print("----------------------------")
            print("      REQUIRED TESTS        ")
            print("----------------------------")
            for i in req:
                if(req[i] == 1 or len(str(req[i]))>1):
                    print('%-20s%-12s' % (i, "PASSED"))
                else:
                    print('%-20s%-12s' % (i, "FAILED"))
            print("==========================")
            
            

        else:
            print("CRITICAL ERROR: Metadata file does not exist in " + z)
            checkFail = 1
        
        
        
        if(checkFail == 1):
            zipFailures = zipFailures + 1
            anyFail = 1
            
        else:
            zipSuccess = zipSuccess + 1
            print("Metadata checks passed for " + z)

    print("")
    print("====================")
    print("All metadata checks complete.")
    print("Successes: " + str(zipSuccess))
    print("Failures: " + str(zipFailures))
    
    if(zipFailures > 0):
        sys.exit("CRITICAL ERROR: At least one Metadata check failed; check the log to see what's wrong.")

else:
    print("No modified zip files found.")
    sys.exit("Error: No zip files found!")