"use client"

import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { UploadCloud, FileText } from "lucide-react"

interface FileSubmitModalProps {
  isOpen: boolean
  onClose: () => void
  onSend: (file: File) => void
}

export default function FileSubmitModal({ isOpen, onClose, onSend }: FileSubmitModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null
    setSelectedFile(f)
  }

  const handleAnalyze = () => {
    if (selectedFile) {
      onSend(selectedFile)
      onClose()
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  const handleDialogChange = (open: boolean) => {
    if (!open) {
      onClose()
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleDialogChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-xl">파일 첨부</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center flex flex-col items-center justify-center bg-gray-50">
            <UploadCloud className="h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-600 mb-4">진단서 사진 또는 보험약관 PDF 1개를 올려주세요</p>

            <Input
              ref={fileInputRef}
              id="file-upload"
              type="file"
              className="hidden"
              onChange={handleFileChange}
              accept=".pdf,image/*"
            />
            <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
              파일 첨부하기
            </Button>

            {selectedFile && (
              <div className="mt-4 text-sm text-gray-700">
                선택됨: <span className="font-medium">{selectedFile.name}</span>
              </div>
            )}
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => handleDialogChange(false)}>취소</Button>
            <Button
              onClick={handleAnalyze}
              disabled={!selectedFile}
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
            >
              <FileText className="mr-2 h-4 w-4" />
              파일 업로드
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
