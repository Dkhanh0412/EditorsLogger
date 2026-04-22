-- DaVinci Resolve Editor's Log Mapper
local ui = fu.UIManager
local disp = bmd.UIDispatcher(ui)

local resolve = Resolve()
local projectManager = resolve:GetProjectManager()
local project = projectManager:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not project or not timeline then
    print("❌ Error: Open a timeline before running.")
    return
end

-- Create window elements
local mapperWindow = disp:AddWindow({
    ID = "MapperWin",
    WindowTitle = "Editor's Log: Phase Mapper",
    Geometry = { 400, 300, 700, 400 },  -- Larger window size
    
    ui:VGroup{
        ID = "root",
        
        ui:Label{ 
            ID = "HeaderLabel",
            Text = "Project: " .. project:GetName() .. " | Timeline: " .. timeline:GetName(), 
            Alignment = { AlignHCenter = true } 
        },
        
        ui:VGap(15),
        
        ui:Label{ 
            ID = "Phase1Label",
            Text = "Phase 1: Extraction", 
            Weight = 0,
            Font = ui:Font{ PixelSize = 14, StyleName = "Bold" }
        },
        
        ui:HGroup{
            ui:Button{ 
                ID = "ExtractBtn", 
                Text = "📸 Extract Midpoint Stills to Gallery", 
                MinimumSize = { 450, 40 }
            },
        },
        
        ui:VGap(15),
        ui:Label{ ID = "Separator1", Text = "───────────────────────────────────────", Alignment = { AlignHCenter = true } },
        ui:VGap(15),
        
        ui:Label{ 
            ID = "Phase2Label",
            Text = "Phase 2: CSV & File Export", 
            Weight = 0,
            Font = ui:Font{ PixelSize = 14, StyleName = "Bold" }
        },
        
        ui:HGroup{
            ui:LineEdit{ 
                ID = "FolderPath", 
                PlaceholderText = "Select destination folder...", 
                ReadOnly = true,
                MinimumSize = { 500, 30 }
            },
            ui:Button{ 
                ID = "BrowseBtn", 
                Text = "Browse", 
                MinimumSize = { 100, 30 }
            },
        },
        
        ui:Button{ 
            ID = "ExportBtn", 
            Text = "📄 Export Mapping CSV & JPEGs", 
            Enabled = false, 
            MinimumSize = { 450, 40 }
        },
        
        ui:VGap(10),
        ui:Label{ 
            ID = "StatusLabel",
            Text = "", 
            Weight = 0,
            Alignment = { AlignHCenter = true }
        },
    }
})

local itm = mapperWindow:GetItems()
local osName = package.config:sub(1,1)

-- PHASE 1: EXTRACTION LOGIC
mapperWindow.On.ExtractBtn.Clicked = function(ev)
    local items = timeline:GetItemListInTrack("video", 1)
    print("🚀 Extracting Midpoint Stills...")
    
    for i, item in ipairs(items) do
        local startFrame = item:GetStart()
        local duration = item:GetEnd() - startFrame
        local midPoint = math.floor(startFrame + (duration * 0.5))
        
        timeline:SetCurrentTimecode(tostring(midPoint))
        timeline:GrabStill()
    end
    
    print("✅ Stills added to Gallery.")
    itm.ExtractBtn.Text = "✅ Stills Extracted to Gallery"
    itm.StatusLabel.Text = "Stills extracted to Gallery. Ready for export."
end

-- BROWSE LOGIC
mapperWindow.On.BrowseBtn.Clicked = function(ev)
    local selectedPath = fu:RequestDir()
    if selectedPath then
        itm.FolderPath.Text = selectedPath
        itm.ExportBtn.Enabled = true
    end
end

-- PHASE 2: CSV & FILE EXPORT
mapperWindow.On.ExportBtn.Clicked = function(ev)
    local folderPath = itm.FolderPath.Text
    local timelineName = timeline:GetName():gsub("[%s%p]", "_")
    local csv_file_path = folderPath .. osName .. "Mapping_" .. timelineName .. ".csv"
    
    local file = io.open(csv_file_path, "w")
    if not file then 
        print("❌ Error: Could not create CSV file.")
        itm.StatusLabel.Text = "❌ Error: Could not create CSV file."
        return 
    end

    file:write("Timeline_Name,Clip_Name,Source_Filename,Still_Path,Notes\n")

    local items = timeline:GetItemListInTrack("video", 1)
    local gallery = project:GetGallery()
    local album = gallery:GetCurrentStillAlbum()
    local stills = album:GetStills()
    
    print("🚀 Exporting Files...")
    itm.StatusLabel.Text = "Exporting files..."
    
    local exportedStills = {}  -- Store references to stills we're exporting
    
    for i, item in ipairs(items) do
        local mediaPoolItem = item:GetMediaPoolItem()
        if mediaPoolItem then
            local props = mediaPoolItem:GetClipProperty()
            local clipName = item:GetName()
            local fileName = props["File Name"] or "Unknown"
            local cleanName = clipName:gsub("%.%w+$", "")
            
            local stillIndex = #stills - (#items - i)
            local currentStill = stills[stillIndex]
            
            if currentStill then
                table.insert(exportedStills, currentStill)  -- Save for cleanup
                local stillFileName = cleanName .. "_Mid"
                
                album:ExportStills({currentStill}, folderPath, stillFileName, "jpg")
                local fullStillPath = folderPath .. osName .. stillFileName .. ".jpg"
                
                local safeClip = clipName:gsub(",", " ")
                local safeFile = fileName:gsub(",", " ")
                file:write(string.format("%s,%s,%s,%s,\n", timeline:GetName(), safeClip, safeFile, fullStillPath))
            end
        end
    end
    
    file:close()
    
    -- CLEANUP: Delete all stills from gallery
    print("🧹 Cleaning up Gallery stills...")
    itm.StatusLabel.Text = "Cleaning up Gallery stills..."
    
    -- Delete all stills from the album
    for i = #stills, 1, -1 do
        album:DeleteStills({stills[i]})
    end
    
    print("✅ Cleanup complete. Gallery stills removed.")
    
    print("✅ Processed " .. #items .. " clips.")
    print("✅ CSV saved to: " .. csv_file_path)
    
    itm.ExtractBtn.Text = "📸 Extract Midpoint Stills to Gallery"  -- Reset button text
    itm.ExportBtn.Text = "✅ Export Complete! (" .. #items .. " clips)"
    itm.ExportBtn.Enabled = false
    itm.StatusLabel.Text = "Export complete! " .. #items .. " clips processed. Gallery stills cleaned up."
end

-- CLOSE HANDLER
mapperWindow.On.MapperWin.Close = function(ev)
    disp:ExitLoop()
end

mapperWindow:Show()
disp:RunLoop()